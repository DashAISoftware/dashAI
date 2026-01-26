import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Card,
  CardContent,
  CardActions,
  Box,
  Typography,
  Chip,
  IconButton,
  Button,
  Collapse,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
  Tooltip,
  Grid,
} from "@mui/material";
import {
  PlayArrow,
  Stop,
  Edit,
  Delete,
  ExpandMore,
  ExpandLess,
  Settings,
  TrendingUp,
  QueryStats,
} from "@mui/icons-material";
import { getRunStatus } from "../../utils/runStatus";
import RunOperations from "./RunOperations";

/**
 * Card component displaying a model run with actions and details
 */
function RunCard({
  run,
  models = [],
  session,
  onTrain,
  onEdit,
  onExplainer,
  onDelete,
  onOperationsRefresh,
  explainerRefreshTrigger,
  isLastRun = false,
}) {
  const [expanded, setExpanded] = useState(false);

  // Get display status from numeric code
  const statusText = getRunStatus(run.status);

  // Get model display name
  const model = models.find((m) => m.name === run.model_name);
  const modelDisplayName = model?.display_name || run.model_name;

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

  // Check if run can be trained
  const canTrain =
    statusText === "Not Started" ||
    statusText === "Error" ||
    statusText === "Finished";
  const isRunning = statusText === "Delivered" || statusText === "Started";

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Get metrics from run
  const getMetrics = () => {
    if (!run.trained_models || run.trained_models.length === 0) {
      return null;
    }

    const metrics = {};
    run.trained_models.forEach((model) => {
      if (model.metrics) {
        Object.entries(model.metrics).forEach(([key, value]) => {
          if (!metrics[key]) metrics[key] = [];
          metrics[key].push(value);
        });
      }
    });

    return metrics;
  };

  const metrics = getMetrics();

  return (
    <Card
      elevation={2}
      sx={{
        mb: 2,
        borderLeft: "4px solid",
        borderLeftColor:
          statusText === "Finished"
            ? "success.main"
            : statusText === "Error"
              ? "error.main"
              : isRunning
                ? "info.main"
                : "grey.500",
      }}
    >
      <CardContent>
        {/* Header: Model Name (User Name) with Status and Actions */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
            gap: 1,
          }}
        >
          {/* Left: Model Name and User Name with Gear */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}>
            <Tooltip title={expanded ? "Hide Parameters" : "View Parameters"}>
              <IconButton
                size="small"
                onClick={() => setExpanded(!expanded)}
                color={expanded ? "primary" : "default"}
              >
                <Settings fontSize="small" />
              </IconButton>
            </Tooltip>
            <Typography
              variant="h6"
              component="div"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                flexWrap: "wrap",
              }}
            >
              {modelDisplayName}
              <Typography
                variant="body2"
                color="text.secondary"
                component="span"
              >
                ({run.name})
              </Typography>
            </Typography>
          </Box>

          {/* Right: Actions and Status */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {/* Train/Re-train Button */}
            {canTrain && (
              <Button
                variant="contained"
                color="primary"
                size="small"
                startIcon={<PlayArrow />}
                onClick={() => onTrain(run)}
                data-tour={isLastRun ? "train-button" : undefined}
              >
                {statusText === "Finished" ? "Re-train" : "Train"}
              </Button>
            )}
            {isRunning && (
              <Button
                variant="contained"
                color="warning"
                size="small"
                disabled
                startIcon={<Stop />}
              >
                Running
              </Button>
            )}

            {/* Status Chip */}
            <Chip
              label={statusText}
              color={getStatusColor(statusText)}
              size="small"
            />

            {/* Delete Button */}
            <Tooltip title="Delete Run">
              <IconButton
                size="small"
                color="error"
                onClick={() => onDelete(run)}
                disabled={isRunning}
              >
                <Delete fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Metrics Summary */}
        {metrics && Object.keys(metrics).length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Metrics
            </Typography>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
              {Object.entries(metrics).map(([metric, values]) => {
                const avgValue =
                  values.reduce((sum, val) => sum + val, 0) / values.length;
                return (
                  <Box key={metric}>
                    <Typography variant="caption" color="text.secondary">
                      {metric.toUpperCase()}
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {avgValue.toFixed(4)}
                    </Typography>
                  </Box>
                );
              })}
            </Box>
          </Box>
        )}

        {/* Description if present */}
        {run.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {run.description}
          </Typography>
        )}

        {/* Expandable Details */}
        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Box sx={{ mt: 2 }}>
            {/* Model Parameters */}
            {run.parameters && Object.keys(run.parameters).length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Model Parameters
                </Typography>
                <TableContainer component={Paper}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Parameter</TableCell>
                        <TableCell>Value</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(run.parameters).map(([key, value]) => (
                        <TableRow key={key}>
                          <TableCell>{key}</TableCell>
                          <TableCell>
                            {typeof value === "object" && value !== null
                              ? value.fixed_value !== undefined
                                ? String(value.fixed_value)
                                : JSON.stringify(value)
                              : String(value)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {/* Optimizer Configuration */}
            {run.optimizer_name && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Optimizer: {run.optimizer_name}
                </Typography>
                {run.optimizer_parameters &&
                  Object.keys(run.optimizer_parameters).length > 0 && (
                    <TableContainer component={Paper}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Parameter</TableCell>
                            <TableCell>Value</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {Object.entries(run.optimizer_parameters).map(
                            ([key, value]) => (
                              <TableRow key={key}>
                                <TableCell>{key}</TableCell>
                                <TableCell>
                                  {typeof value === "object"
                                    ? JSON.stringify(value)
                                    : String(value)}
                                </TableCell>
                              </TableRow>
                            ),
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
              </Box>
            )}

            {/* Goal Metric */}
            {run.goal_metric && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Goal Metric: <strong>{run.goal_metric}</strong>
                </Typography>
              </Box>
            )}
          </Box>
        </Collapse>

        {/* RunOperations - Separate section for finished runs */}
        {statusText === "Finished" && (
          <Box sx={{ mt: 2 }}>
            <RunOperations
              run={run}
              session={session}
              onRefresh={onOperationsRefresh}
              explainerRefreshTrigger={explainerRefreshTrigger}
            />
          </Box>
        )}
      </CardContent>

      <Divider />

      <CardActions sx={{ justifyContent: "flex-end", px: 2, py: 1 }}>
        {/* Edit button */}
        <IconButton
          size="small"
          onClick={() => onEdit(run)}
          color="primary"
          disabled={isRunning}
          title="Edit parameters"
        >
          <Edit fontSize="small" />
        </IconButton>
      </CardActions>
    </Card>
  );
}

RunCard.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    model_name: PropTypes.string,
    status: PropTypes.number,
    parameters: PropTypes.object,
    optimizer_name: PropTypes.string,
    optimizer_parameters: PropTypes.object,
    goal_metric: PropTypes.string,
    description: PropTypes.string,
    created: PropTypes.string,
    trained_models: PropTypes.array,
    experiment_id: PropTypes.number,
  }).isRequired,
  models: PropTypes.array,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onTrain: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onExplainer: PropTypes.func,
  onDelete: PropTypes.func.isRequired,
  onOperationsRefresh: PropTypes.func,
  explainerRefreshTrigger: PropTypes.number,
};

export default RunCard;
