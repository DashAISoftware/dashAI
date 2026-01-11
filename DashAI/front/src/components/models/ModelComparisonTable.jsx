import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";
import { Box, IconButton, Tooltip } from "@mui/material";
import { PlayArrow, Delete, Visibility } from "@mui/icons-material";
import { getRunStatus } from "../../utils/runStatus";
import { getComponents } from "../../api/component";

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

  const getRows = () => {
    return runs.map((run) => {
      const row = {
        id: run.id,
        name: run.name,
        model_name: run.model_name,
        status: getRunStatus(run.status),
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

      return {
        field: metricField,
        headerName: metricName,
        width: 120,
        renderCell: (params) => {
          const { statusCode } = params.row;
          const isRunning = statusCode === 1 || statusCode === 2;

          if (isRunning) return "-";
          if (params.value === null || params.value === undefined) return "-";

          const value = Number(params.value);
          if (isNaN(value)) return params.value;

          return value.toFixed(4);
        },
      };
    });
  };

  const columns = [
    {
      field: "name",
      headerName: "Model Name",
      flex: 1,
      minWidth: 150,
    },
    {
      field: "model_name",
      headerName: "Model",
      flex: 1,
      minWidth: 150,
      valueGetter: (value) => {
        const model = models.find((m) => m.name === value);
        return model?.display_name || value;
      },
    },
    ...getMetricColumns(),
    {
      field: "actions",
      headerName: "Actions",
      width: 150,
      sortable: false,
      renderCell: (params) => {
        const canTrain =
          params.row.status === "Not Started" ||
          params.row.status === "Error" ||
          params.row.status === "Finished";
        const isRunning =
          params.row.status === "Delivered" || params.row.status === "Started";

        return (
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <Tooltip title="Train">
              <span>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onTrain(runs.find((r) => r.id === params.row.id));
                  }}
                  disabled={!canTrain}
                  color="primary"
                >
                  <PlayArrow fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>

            <Tooltip title="View Details">
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewDetails(runs.find((r) => r.id === params.row.id));
                }}
                color="default"
              >
                <Visibility fontSize="small" />
              </IconButton>
            </Tooltip>

            <Tooltip title="Delete">
              <span>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(runs.find((r) => r.id === params.row.id));
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

  const rows = getRows();

  return (
    <Box sx={{ height: "100%", width: "100%" }}>
      <DataGrid
        rows={rows}
        columns={columns}
        disableRowSelectionOnClick
        density="compact"
        hideFooter
        onRowClick={(params) => {
          if (onRowClick) {
            onRowClick(params.row.id);
          }
        }}
        initialState={{
          density: "compact",
        }}
        sx={{
          backgroundColor: "background.box",
          "& .MuiDataGrid-row": {
            cursor: onRowClick ? "pointer" : "default",
          },
          "& .MuiDataGrid-virtualScroller": {
            marginBottom: "8px",
          },
          "& .MuiDataGrid-columnHeaders": {
            backgroundColor: "background.box",
          },
        }}
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
