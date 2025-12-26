import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";
import { Box, Chip, IconButton, Tooltip } from "@mui/material";
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

  // Transform runs to rows with flattened metrics
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

      // Extract test metrics
      if (run.test_metrics) {
        Object.entries(run.test_metrics).forEach(([key, value]) => {
          row[`test_${key}`] =
            typeof value === "number"
              ? Math.trunc(value * 10000) / 10000
              : value;
        });
      }

      // Extract train metrics
      if (run.train_metrics) {
        Object.entries(run.train_metrics).forEach(([key, value]) => {
          row[`train_${key}`] =
            typeof value === "number"
              ? Math.trunc(value * 10000) / 10000
              : value;
        });
      }

      // Extract validation metrics
      if (run.validation_metrics) {
        Object.entries(run.validation_metrics).forEach(([key, value]) => {
          row[`val_${key}`] =
            typeof value === "number"
              ? Math.trunc(value * 10000) / 10000
              : value;
        });
      }

      return row;
    });
  };

  // Get all unique metrics from runs
  const getMetricColumns = () => {
    const metricsSet = new Set();

    runs.forEach((run) => {
      if (run.test_metrics) {
        Object.keys(run.test_metrics).forEach((key) =>
          metricsSet.add(`test_${key}`),
        );
      }
    });

    return Array.from(metricsSet).map((metricField) => ({
      field: metricField,
      headerName: metricField.toLowerCase(),
      width: 120,
      renderCell: (params) => {
        const { statusCode } = params.row;
        const isRunning = statusCode === 1 || statusCode === 2; // Delivered or Started

        return isRunning ? "-" : params.value || "-";
      },
    }));
  };

  // Status color mapping
  const getStatusColor = (status) => {
    switch (status) {
      case "Not Started":
        return "default";
      case "Delivered":
      case "Started":
        return "info";
      case "Finished":
        return "success";
      case "Error":
        return "error";
      default:
        return "default";
    }
  };

  const columns = [
    {
      field: "name",
      headerName: "Run Name",
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
    {
      field: "status",
      headerName: "Status",
      width: 130,
      renderCell: (params) => (
        <Chip
          label={params.value}
          color={getStatusColor(params.value)}
          size="small"
        />
      ),
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
    <Box sx={{ height: "100%", width: "100%", pb: 1 }}>
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
};

export default ModelComparisonTable;
