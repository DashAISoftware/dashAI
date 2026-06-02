import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { useTheme } from "@mui/material/styles";
import {
  Box,
  IconButton,
  MenuItem,
  Select,
  Tooltip,
  Typography,
} from "@mui/material";
import { PlayArrow, Delete, Visibility } from "@mui/icons-material";
import { getComponents } from "../../api/component";
import { useTranslation } from "react-i18next";
import { useTableLocalization } from "../../utils/useTableLocalization";
import api from "../../api/api";
import DeleteConfirmationModal from "../threeSectionLayout/DeleteConfirmationModal";

/**
 * Compact comparison table showing all runs in a session.
 * Designed for sticky header display with fixed height.
 *
 * Scores are computed server-side and fetched from the backend.
 */
function ModelComparisonTable({
  runs: initialRuns = [],
  session,
  onTrain,
  onViewDetails,
  onDelete,
  onRowClick,
  metricSplit = "test",
}) {
  const [models, setModels] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [scores, setScores] = useState({});
  const [loadingScores, setLoadingScores] = useState(false);
  const [runs, setRuns] = useState(initialRuns);
  const [runToDelete, setRunToDelete] = useState(null);

  const { t } = useTranslation(["models", "common"]);
  const theme = useTheme();
  const localization = useTableLocalization();

  // ────────────────────────────────────────────────────────────────────────
  // Sync initial runs prop with local state
  // ────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    setRuns(initialRuns);
  }, [initialRuns]);

  // ────────────────────────────────────────────────────────────────────────
  // Fetch models and metrics
  // ────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await getComponents({ selectTypes: ["Model"] });
        setModels(response);
      } catch (error) {
        console.error("Error fetching models:", error);
      }
    };
    fetchModels();
  }, []);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await getComponents({ selectTypes: ["Metric"] });
        setMetrics(response);
      } catch (error) {
        console.error("Error fetching metrics:", error);
      }
    };
    fetchMetrics();
  }, []);

  // ────────────────────────────────────────────────────────────────────────
  // Fetch scoring profiles for this session's task
  // ────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    const fetchProfiles = async () => {
      try {
        const params = {};
        if (session?.task_name) {
          params.task_name = session.task_name;
        }
        const response = await api.get("/v1/scoring/profiles", { params });
        const profilesList = response.data;
        setProfiles(profilesList);

        // Keep current profile only if still valid; otherwise select first
        setSelectedProfile((prevProfile) => {
          if (profilesList.length === 0) {
            return null;
          }
          const profileExists = profilesList.some((p) => p.id === prevProfile);
          return profileExists ? prevProfile : profilesList[0].id;
        });
      } catch (error) {
        console.error("Error fetching scoring profiles:", error);
      }
    };
    fetchProfiles();
  }, [session?.task_name]);

  // Stable string that changes only when a run's status changes.
  // Used as a dep so the score fetch re-triggers after training completes
  // without firing on every unrelated re-render of the parent.
  const runStatusSignature = useMemo(
    () => initialRuns.map((r) => `${r.id}:${r.status}`).join(","),
    [initialRuns],
  );

  // ────────────────────────────────────────────────────────────────────────
  // Fetch scores when profile, split, session or any run status changes
  // ────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!initialRuns.length || !selectedProfile || !session?.id) return;

    const fetchScores = async () => {
      setLoadingScores(true);
      try {
        const response = await api.get("/v1/run/", {
          params: {
            model_session_id: session.id,
            include_scores: true,
            profile_id: selectedProfile,
            metric_split: metricSplit,
          },
        });

        // Update runs with metrics and scores
        setRuns(response.data);

        // Extract scores into separate map for easy lookup
        const scoresMap = {};
        response.data.forEach((run) => {
          if (run.score) {
            scoresMap[run.id] = run.score;
          }
        });
        setScores(scoresMap);
      } catch (error) {
        console.error("Error fetching scores:", error);
      } finally {
        setLoadingScores(false);
      }
    };

    fetchScores();
  }, [selectedProfile, metricSplit, session?.id, runStatusSignature]);

  // ────────────────────────────────────────────────────────────────────────
  // Build columns
  // ────────────────────────────────────────────────────────────────────────

  const isCrossValidation =
    session.evaluation_strategy === "CrossValidationEvaluationStrategy";

  // Run type color using existing theme.palette.accent tokens
  const getRunType = (run) => {
    if (run.nested) return "nestedCv";
    if (run.optimizer_name) return "hpo";
    return "noHpo";
  };

  const runTypeStyles = {
    noHpo: {
      bg: theme.palette.accent.amberDim,
      border: theme.palette.accent.amberBorder,
      color: theme.palette.accent.amber,
    },
    hpo: {
      bg: theme.palette.accent.tealDim,
      border: theme.palette.accent.tealBorder,
      color: theme.palette.accent.teal,
    },
    nestedCv: {
      bg: theme.palette.accent.purpleDim,
      border: theme.palette.accent.purpleBorder,
      color: theme.palette.accent.purple,
    },
  };

  const getMetricColumns = () => {
    const metricsSet = new Set();
    const prefix = metricSplit === "validation" ? "val" : metricSplit;

    runs.forEach((run) => {
      const metricsKey = `${metricSplit}_metrics`;
      if (run[metricsKey]) {
        Object.keys(run[metricsKey]).forEach((key) =>
          metricsSet.add(`${prefix}_${key}`),
        );
      }
    });

    // Compute best value per metric field
    const bestValues = {};
    Array.from(metricsSet).forEach((metricField) => {
      const metricName = metricField.replace(/^(test|train|val)_/, "");
      const metricInfo = metrics.find((m) => m.name === metricName);
      const maximize = metricInfo?.metadata?.maximize;
      if (maximize === undefined || maximize === null) return;

      const metricsKey = `${metricSplit}_metrics`;
      const values = runs
        .filter(
          (run) =>
            run[metricsKey]?.[metricName] !== undefined &&
            run[metricsKey]?.[metricName] !== null,
        )
        .map((run) => Number(run[metricsKey][metricName]))
        .filter((v) => !isNaN(v));

      if (values.length > 0) {
        bestValues[metricField] = maximize
          ? Math.max(...values)
          : Math.min(...values);
      }
    });

    return Array.from(metricsSet).map((metricField) => {
      const metricName = metricField.replace(/^(test|train|val)_/, "");
      const metricInfo = metrics.find((m) => m.name === metricName);
      const metricDescription = metricInfo?.description || metricName;
      const maximize = metricInfo?.metadata?.maximize;

      const directionArrow =
        maximize === true ? "↑" : maximize === false ? "↓" : "";
      const directionLabel =
        maximize === true
          ? t("models:label.higherIsBetter")
          : maximize === false
            ? t("models:label.lowerIsBetter")
            : "";

      const tooltipContent = directionLabel
        ? `${metricDescription} — ${directionLabel}`
        : metricDescription;

      const bestVal = bestValues[metricField];
      const metricsKey = `${metricSplit}_metrics`;

      return {
        id: metricField,
        accessorFn: (row) => row[metricsKey]?.[metricName],
        header: `${metricName} ${directionArrow}`.trim(),
        size: 120,
        Header: () => (
          <Tooltip title={tooltipContent} arrow placement="top">
            <Box
              sx={{
                cursor: "help",
                width: "100%",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {metricName}
              {directionArrow && (
                <Box component="span" sx={{ ml: 1, opacity: 0.7 }}>
                  {directionArrow}
                </Box>
              )}
            </Box>
          </Tooltip>
        ),
        Cell: ({ row, cell }) => {
          const { status } = row.original;
          const isRunning = status === 1 || status === 2;

          if (isRunning) return "-";
          const val = cell.getValue();
          if (val === null || val === undefined) return "-";

          const value = Number(val);
          if (isNaN(value)) return val;

          const formatted = value.toFixed(4);
          const isBest =
            bestVal !== undefined && Math.abs(value - bestVal) < 1e-9;

          // Get standard deviation for CV sessions
          let stdValue = null;
          if (isCrossValidation) {
            const stdMetricsKey = `${metricSplit}_metrics_std`;
            stdValue = row.original[stdMetricsKey]?.[metricName];
          }

          return (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 0.25,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                {isBest && (
                  <Tooltip title={t("models:label.bestModel")} placement="top">
                    <Box
                      component="span"
                      sx={{ color: "warning.main", lineHeight: 1 }}
                    >
                      ★
                    </Box>
                  </Tooltip>
                )}
                <Box>{formatted}</Box>
              </Box>
              {isCrossValidation && stdValue !== null && (
                <Box sx={{ fontSize: "0.9em", color: "text.secondary" }}>
                  ±{Number(stdValue).toFixed(4)}
                </Box>
              )}
            </Box>
          );
        },
      };
    });
  };

  const data = useMemo(() => runs, [runs]);

  const columns = useMemo(() => {
    const scoreColumn = {
      id: "score",
      header: t("models:label.score"),
      size: 90,
      accessorFn: (row) => scores[row.id]?.score ?? -1,
      Header: () => (
        <Tooltip
          title={t("models:label.scoreHeaderTooltip")}
          arrow
          placement="top"
        >
          <Box sx={{ fontWeight: "bold", cursor: "help" }}>
            {t("models:label.score")}
          </Box>
        </Tooltip>
      ),
      Cell: ({ row }) => {
        const { status, id } = row.original;
        const isRunning = status === 1 || status === 2;
        if (isRunning) return "-";

        const scoreData = scores[id];
        if (!scoreData) return "-";

        const { score, breakdown } = scoreData;

        // Find the best score across all runs
        const allScores = Object.values(scores)
          .filter((s) => s && s.score !== undefined)
          .map((s) => s.score);
        const bestScore = allScores.length > 0 ? Math.max(...allScores) : null;
        const isBest = bestScore !== null && Math.abs(score - bestScore) < 1e-6;

        const tooltipContent = (
          <Typography variant="body2" component="div" sx={{ lineHeight: 1.6 }}>
            <Typography
              variant="body2"
              component="div"
              sx={{ fontWeight: "bold", mb: 1 }}
            >
              {t("models:label.score")}: {score.toFixed(1)}/100
            </Typography>
            {breakdown.map(({ metric_name, value, normalized_weight }, i) => (
              <Typography variant="body2" component="div" key={metric_name}>
                {i === 0 ? "=" : "+"} {metric_name} ({value.toFixed(4)}) ×{" "}
                {(normalized_weight * 100).toFixed(0)}%
              </Typography>
            ))}
          </Typography>
        );

        return (
          <Tooltip title={tooltipContent} placement="top" arrow>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                cursor: "help",
                fontWeight: "bold",
              }}
            >
              {isBest && (
                <Box component="span" sx={{ color: "warning.main" }}>
                  ★
                </Box>
              )}
              {score.toFixed(1)}
            </Box>
          </Tooltip>
        );
      },
    };

    return [
      {
        accessorKey: "name",
        header: t("common:modelName"),
        size: 120,
        Cell: ({ cell }) => (
          <Tooltip title={cell.getValue()} placement="top" arrow>
            <Box
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                width: "120px",
              }}
            >
              {cell.getValue()}
            </Box>
          </Tooltip>
        ),
      },
      {
        accessorKey: "model_name",
        header: t("common:model"),
        size: 120,
        accessorFn: (row) => {
          const model = models.find((m) => m.name === row.model_name);
          return model?.display_name || row.model_name;
        },
        Cell: ({ cell }) => (
          <Tooltip title={cell.getValue()} placement="top" arrow>
            <Box
              sx={{
                width: "120px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {cell.getValue()}
            </Box>
          </Tooltip>
        ),
      },
      scoreColumn,
      ...getMetricColumns(),
      {
        id: "actions",
        header: t("common:actions"),
        enableSorting: false,
        enableColumnFilter: false,
        size: 150,
        Cell: ({ row }) => {
          const canTrain =
            row.original.status === 0 ||
            row.original.status === 4 ||
            row.original.status === 3;
          const isRunning =
            row.original.status === 1 || row.original.status === 2;

          return (
            <Box sx={{ display: "flex", gap: 1 }}>
              <Tooltip title={t("common:train")}>
                <span>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onTrain(runs.find((r) => r.id === row.original.id));
                    }}
                    disabled={!canTrain}
                    color="primary"
                  >
                    <PlayArrow fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>

              <Tooltip title={t("common:viewDetails")}>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewDetails(runs.find((r) => r.id === row.original.id));
                  }}
                  color="default"
                >
                  <Visibility fontSize="small" />
                </IconButton>
              </Tooltip>

              <Tooltip title={t("common:delete")}>
                <span>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      setRunToDelete(
                        runs.find((r) => r.id === row.original.id),
                      );
                    }}
                    disabled={isRunning}
                    color="error"
                  >
                    <Delete fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
            </Box>
          );
        },
      },
    ];
  }, [
    models,
    metrics,
    runs,
    scores,
    metricSplit,
    t,
    onTrain,
    onViewDetails,
    onDelete,
  ]);

  const columnOrder = useMemo(
    () => columns.map((col) => col.id ?? col.accessorKey).filter(Boolean),
    [columns],
  );

  const table = useMaterialReactTable({
    columns,
    data,
    mrtTheme: { baseBackgroundColor: theme.palette.background.box },
    muiTablePaperProps: {
      elevation: 0,
      sx: {
        height: "100%",
        display: "flex",
        flexDirection: "column",
        border: "1px solid",
        borderColor: "divider",
      },
    },
    muiTableContainerProps: { sx: { flex: 1, overflow: "auto" } },
    localization,
    initialState: { density: "compact" },
    enableStickyHeader: true,
    enableRowSelection: false,
    enablePagination: false,
    enableTopToolbar: false,
    enableBottomToolbar: false,
    muiTableBodyCellProps: { sx: { py: 1, whiteSpace: "pre" } },
    muiTableHeadCellProps: { sx: { py: 1 } },
    state: { columnOrder },
    muiTableBodyRowProps: ({ row }) => {
      const runType = getRunType(row.original);
      const { bg, border } = runTypeStyles[runType];
      return {
        onClick: () => {
          if (onRowClick) onRowClick(row.original.id);
        },
        sx: {
          cursor: onRowClick ? "pointer" : "default",
          backgroundColor: bg,
          borderLeft: `3px solid ${border}`,
          "&:hover td": { backgroundColor: "transparent" },
        },
      };
    },
  });

  const activeProfile = profiles.find((p) => p.id === selectedProfile);
  const profileWeightsLabel = activeProfile
    ? Object.entries(activeProfile.weights)
        .map(([metric, w]) => `${metric}: ${(w * 100).toFixed(0)}%`)
        .join(" · ")
    : "";

  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Profile selector */}
      <Box
        sx={{
          px: 3,
          py: 1,
          display: "flex",
          alignItems: "center",
          gap: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
          flexShrink: 0,
          flexWrap: "wrap",
        }}
      >
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ whiteSpace: "nowrap" }}
        >
          {t("models:label.scoreProfile")}:
        </Typography>
        <Select
          value={selectedProfile || ""}
          onChange={(e) => setSelectedProfile(e.target.value)}
          size="small"
          disabled={profiles.length === 0 || loadingScores}
          sx={{
            fontSize: "0.75rem",
            height: 24,
            "& .MuiSelect-select": { py: 0, px: 1 },
          }}
        >
          {profiles.map((p) => (
            <MenuItem key={p.id} value={p.id} sx={{ fontSize: "0.8rem" }}>
              {t(`models:label.profile_${p.id}`)}
            </MenuItem>
          ))}
        </Select>
        <Typography variant="caption" color="text.secondary">
          {profileWeightsLabel}
        </Typography>
        {loadingScores && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ ml: "auto" }}
          >
            {t("common:loading")}
          </Typography>
        )}

        {/* Run type legend — right side of profile bar */}
        <Box
          sx={{
            ml: loadingScores ? 2 : "auto",
            display: "flex",
            alignItems: "center",
            gap: 2,
          }}
        >
          {[
            { key: "noHpo", label: t("models:label.runType.noHpo", "Sin HPO") },
            { key: "hpo", label: t("models:label.runType.hpo", "Con HPO") },
            ...(isCrossValidation
              ? [
                  {
                    key: "nestedCv",
                    label: t("models:label.runType.nestedCv", "Nested CV"),
                  },
                ]
              : []),
          ].map(({ key, label }) => (
            <Box
              key={key}
              sx={{ display: "flex", alignItems: "center", gap: 0.75 }}
            >
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "2px",
                  backgroundColor: runTypeStyles[key].bg,
                  border: `1.5px solid ${runTypeStyles[key].border}`,
                  flexShrink: 0,
                }}
              />
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ whiteSpace: "nowrap" }}
              >
                {label}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Table */}
      <Box sx={{ flex: 1, minHeight: 0 }}>
        <MaterialReactTable table={table} />
      </Box>

      <DeleteConfirmationModal
        open={Boolean(runToDelete)}
        onClose={() => setRunToDelete(null)}
        onConfirm={() => {
          onDelete(runToDelete);
          setRunToDelete(null);
        }}
        content={t("models:message.confirmDeleteRun")}
      />
    </Box>
  );
}

ModelComparisonTable.propTypes = {
  runs: PropTypes.array.isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onTrain: PropTypes.func.isRequired,
  onViewDetails: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onRowClick: PropTypes.func,
  metricSplit: PropTypes.oneOf(["train", "validation", "test"]),
};

export default ModelComparisonTable;
