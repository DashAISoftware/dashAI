import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import {
  Box,
  Chip,
  IconButton,
  MenuItem,
  Select,
  Tooltip,
  Typography,
} from "@mui/material";
import { PlayArrow, Delete, Visibility } from "@mui/icons-material";
import { getComponents } from "../../api/component";
import { useTranslation } from "react-i18next";
import api from "../../api/api";

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
  selectedRunId = null,
}) {
  const [models, setModels] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [scores, setScores] = useState({});
  const [loadingScores, setLoadingScores] = useState(false);
  const [runs, setRuns] = useState(initialRuns);

  const { t, i18n } = useTranslation(["models", "common"]);
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

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

  // ────────────────────────────────────────────────────────────────────────
  // Fetch scores when profile or runs change
  // ────────────────────────────────────────────────────────────────────────

  const completedRunIds = useMemo(
    () =>
      runs
        .filter((r) => r.status === 3)
        .map((r) => r.id)
        .join(","),
    [runs],
  );

  useEffect(() => {
    if (!runs.length || !selectedProfile || !session?.id) return;

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
  }, [selectedProfile, metricSplit, session?.id, completedRunIds]);

  // ────────────────────────────────────────────────────────────────────────
  // Build columns
  // ────────────────────────────────────────────────────────────────────────

  // Returns true if this run used nested CV
  const isNestedCV = (run) => run.nested !== null && run.nested !== undefined;

  // Returns the correct metrics key depending on nested CV
  const getMetricsKey = (run, split) => {
    const base =
      split === "validation" ? "validation_metrics" : `${split}_metrics`;
    return isNestedCV(run) ? `${base}_outer` : base;
  };

  const getMetricColumns = () => {
    const metricsSet = new Set();
    const prefix = metricSplit === "validation" ? "val" : metricSplit;

    runs.forEach((run) => {
      // Collect metric names from both regular and outer keys
      // so columns are stable regardless of which runs are present
      const baseKey = `${metricSplit}_metrics`;
      const outerKey = `${metricSplit}_metrics_outer`;
      [baseKey, outerKey].forEach((key) => {
        if (run[key] && Object.keys(run[key]).length > 0) {
          Object.keys(run[key]).forEach((m) =>
            metricsSet.add(`${prefix}_${m}`),
          );
        }
      });
    });

    // Compute best value per metric field
    const bestValues = {};
    Array.from(metricsSet).forEach((metricField) => {
      const metricName = metricField.replace(/^(test|train|val)_/, "");
      const metricInfo = metrics.find((m) => m.name === metricName);
      const maximize = metricInfo?.metadata?.maximize;
      if (maximize === undefined || maximize === null) return;

      const values = runs
        .filter((run) => {
          const k = getMetricsKey(run, metricSplit);
          const val = run[k]?.[metricName];
          return val !== undefined && val !== null;
        })
        .map((run) => {
          const k = getMetricsKey(run, metricSplit);
          const metricData = run[k]?.[metricName];
          // Handle direct number or object with value and std_value
          const value = metricData?.value ?? metricData;
          return Number(value);
        })
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

      return {
        id: metricField,
        accessorFn: (row) => {
          const key = getMetricsKey(row, metricSplit);
          return row[key]?.[metricName]?.value ?? row[key]?.[metricName];
        },
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
                <Box component="span" sx={{ ml: 0.5, opacity: 0.7 }}>
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

          const resolvedKey = getMetricsKey(row.original, metricSplit);
          // Fallback to the other key if primary has no data
          const baseKey = `${metricSplit}_metrics`;
          const outerKey = `${metricSplit}_metrics_outer`;
          const fallbackKey = resolvedKey === outerKey ? baseKey : outerKey;
          const metricData =
            row.original[resolvedKey]?.[metricName] ??
            row.original[fallbackKey]?.[metricName];
          const val = metricData?.value ?? metricData;

          if (val === null || val === undefined) return "-";

          const value = Number(val);
          if (isNaN(value)) return val;

          const formatted = value.toFixed(4);
          const isBest =
            bestVal !== undefined && Math.abs(value - bestVal) < 1e-9;

          // Get std_value if available
          const stdValue = metricData?.std_value;
          const stdFormatted =
            stdValue !== null && stdValue !== undefined
              ? `±${Number(stdValue).toFixed(4)}`
              : "";

          const isNested = isNestedCV(row.original);
          const nestedSuffix = isNested
            ? ` — ${t("models:tooltip.nestedCVMetric")}`
            : "";
          const tooltipTitle = stdFormatted
            ? `${formatted} ${stdFormatted}${nestedSuffix}`
            : `${formatted}${nestedSuffix}`;

          return (
            <Tooltip title={tooltipTitle} placement="top" arrow>
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
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}
                >
                  <Box>{formatted}</Box>
                  {stdFormatted && (
                    <Box sx={{ fontSize: "0.75rem", opacity: 0.7 }}>
                      {stdFormatted}
                    </Box>
                  )}
                </Box>
              </Box>
            </Tooltip>
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
              sx={{ fontWeight: "bold", mb: 0.5 }}
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
                gap: 0.5,
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
        size: 160,
        Cell: ({ cell, row }) => {
          const run = row.original;
          const hasOptimizer = run.optimizer_name?.trim();
          const nested = isNestedCV(run);
          const chipLabel = nested ? "Nested CV" : hasOptimizer ? "HPO" : null;
          const chipColor = nested ? "secondary" : "primary";
          const chipTooltip = nested
            ? t("models:tooltip.nestedCVRun")
            : t("models:tooltip.hpoRun");
          return (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Tooltip title={cell.getValue()} placement="top" arrow>
                <Box
                  sx={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    minWidth: 0,
                    flex: 1,
                  }}
                >
                  {cell.getValue()}
                </Box>
              </Tooltip>
              {chipLabel && (
                <Tooltip title={chipTooltip} placement="top" arrow>
                  <Chip
                    label={chipLabel}
                    color={chipColor}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: "0.65rem", height: 18, flexShrink: 0 }}
                  />
                </Tooltip>
              )}
            </Box>
          );
        },
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
            <Box sx={{ display: "flex", gap: 0.5 }}>
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
                      onDelete(runs.find((r) => r.id === row.original.id));
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

  // Determine row background color based on HPO configuration
  const getRowBackgroundColor = (run) => {
    const hasOptimizer = run.optimizer_name && run.optimizer_name.trim() !== "";
    const hasNested = run.nested !== null && run.nested !== undefined;

    if (!hasOptimizer) {
      // No HPO - neutral gray
      return theme.palette.mode === "dark"
        ? "rgba(128, 128, 128, 0.15)" // gray with opacity
        : "rgba(128, 128, 128, 0.1)";
    }

    if (hasNested) {
      // Nested CV - purple
      return theme.palette.mode === "dark"
        ? "rgba(156, 39, 176, 0.15)" // purple with opacity
        : "rgba(156, 39, 176, 0.1)";
    }

    // Normal HPO - blue
    return theme.palette.mode === "dark"
      ? "rgba(33, 150, 243, 0.15)" // blue with opacity
      : "rgba(33, 150, 243, 0.1)";
  };

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
    muiTableBodyCellProps: { sx: { py: 0.25, whiteSpace: "pre" } },
    muiTableHeadCellProps: { sx: { py: 0.5 } },
    state: { columnOrder },
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        if (onRowClick) {
          onRowClick(row.original.id);
        }
      },
      sx: {
        cursor: onRowClick ? "pointer" : "default",
        backgroundColor:
          selectedRunId === row.original.id
            ? theme.palette.action.hover
            : getRowBackgroundColor(row.original),
        transition: "background-color 0.2s ease",
        "&:hover": {
          backgroundColor: theme.palette.action.hover,
        },
      },
    }),
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
          px: 1.5,
          py: 0.5,
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
      </Box>

      {/* Table */}
      <Box sx={{ flex: 1, minHeight: 0 }}>
        <MaterialReactTable table={table} />
      </Box>
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
  selectedRunId: PropTypes.number,
};

export default ModelComparisonTable;
