import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { Box, IconButton, Tooltip } from "@mui/material";
import { PlayArrow, Delete, Visibility } from "@mui/icons-material";
import { getRunStatus } from "../../utils/runStatus";
import { getComponents } from "../../api/component";
import { useTranslation } from "react-i18next";

/**
 * Compact comparison table showing all runs in a session
 * Designed for sticky header display with fixed height
 */
function ModelComparisonTable({
  runs = [],
  session,
  onTrain,
  onViewDetails,
  onDelete,
  onRowClick,
  metricSplit = "test",
}) {
  const [models, setModels] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const { t, i18n } = useTranslation(["models", "common"]);
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

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

  const getRows = () => {
    return runs.map((run) => {
      const row = {
        id: run.id,
        name: run.name,
        model_name: run.model_name,
        status: run.status,
        statusCode: run.status,
        created: run.created,
        last_modified: run.last_modified,
      };

      if (run.test_metrics) {
        Object.entries(run.test_metrics).forEach(([key, value]) => {
          row[`test_${key}`] = value;
        });
      }

      if (run.train_metrics) {
        Object.entries(run.train_metrics).forEach(([key, value]) => {
          row[`train_${key}`] = value;
        });
      }

      if (run.validation_metrics) {
        Object.entries(run.validation_metrics).forEach(([key, value]) => {
          row[`val_${key}`] = value;
        });
      }

      return row;
    });
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

    return Array.from(metricsSet).map((metricField) => {
      const metricName = metricField.replace(/^(test|train|val)_/, "");
      const metricInfo = metrics.find((m) => m.name === metricName);
      const metricDescription = metricInfo?.description || metricName;

      return {
        accessorKey: metricField,
        header: metricName,
        size: 120,
        Header: () => (
          <Tooltip title={metricDescription} arrow placement="top">
            <Box
              sx={{
                cursor: "help",
                width: "100%",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {metricName}
            </Box>
          </Tooltip>
        ),
        Cell: ({ row, cell }) => {
          const { statusCode } = row.original;
          const isRunning = statusCode === 1 || statusCode === 2;

          if (isRunning) return "-";
          const val = cell.getValue();
          if (val === null || val === undefined) return "-";

          const value = Number(val);
          if (isNaN(value)) return val;

          return value.toFixed(4);
        },
      };
    });
  };

  const data = useMemo(() => getRows(), [runs]);

  const columns = useMemo(
    () => [
      {
        accessorKey: "name",
        header: t("common:modelName"),
        minSize: 150,
        grow: 1,
      },
      {
        accessorKey: "model_name",
        header: t("common:model"),
        minSize: 150,
        grow: 1,
        accessorFn: (row) => {
          const model = models.find((m) => m.name === row.model_name);
          return model?.display_name || row.model_name;
        },
      },
      ...getMetricColumns(),
      {
        id: "actions",
        header: t("common:actions"),
        enableSorting: false,
        enableColumnFilter: false,
        size: 150,
        Cell: ({ row }) => {
          const canTrain =
            row.original.status === 0 || // Not Started
            row.original.status === 4 || // Error
            row.original.status === 3; // Finished
          const isRunning =
            row.original.status === 1 || row.original.status === 2; // Delivered or Started

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
    ],
    [models, metrics, runs, metricSplit, t, onTrain, onViewDetails, onDelete],
  );

  const table = useMaterialReactTable({
    columns,
    data,
    mrtTheme: { baseBackgroundColor: theme.palette.background.box },
    muiTablePaperProps: { elevation: 0 },
    localization,
    initialState: { density: "compact" },
    enableRowSelection: false,
    enablePagination: false,
    enableTopToolbar: false,
    enableBottomToolbar: false,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        if (onRowClick) {
          onRowClick(row.original.id);
        }
      },
      sx: { cursor: onRowClick ? "pointer" : "default" },
    }),
  });

  return (
    <Box sx={{ height: "100%", width: "100%" }}>
      <MaterialReactTable table={table} />
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
