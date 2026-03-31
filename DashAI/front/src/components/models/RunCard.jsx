import React, { useState, useEffect, useMemo, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Card,
  CardContent,
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
  TextField,
  Alert,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  PlayArrow,
  Stop,
  Edit,
  Delete,
  Save,
  Cancel,
  ExpandMore,
  ExpandLess,
} from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { getRunStatus } from "../../utils/runStatus";
import RunResults from "./RunResults";
import FormSchemaWithSelectedModel from "../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../shared/FormSchemaContainer";
import OptimizationTableSelectOptimizer from "./modelSession/OptimizationTableSelectOptimizer";
import ModelsTableSelectMetric from "./modelSession/ModelsTableSelectMetric";
import useSchema from "../../hooks/useSchema";
import { updateRunParameters, getRunOperationsCount } from "../../api/run";
import RetrainConfirmDialog from "./RetrainConfirmDialog";
import { renderParamValue } from "./ModelParamBlock";
import { useTranslation } from "react-i18next";

const EMPTY_ARRAY = [];

/**
 * Card component displaying a model run with actions and details
 */
function RunCard({
  run,
  models = EMPTY_ARRAY,
  session,
  onTrain,
  onDelete,
  onOperationsRefresh,
  explainerRefreshTrigger,
  isLastRun = false,
  existingRuns = EMPTY_ARRAY,
  onRefresh,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const [expanded, setExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(run.name || "");
  const [editedParameters, setEditedParameters] = useState(
    run.parameters || {},
  );
  const [editedOptimizer, setEditedOptimizer] = useState(
    run.optimizer_name || "",
  );
  const [editedOptimizerParams, setEditedOptimizerParams] = useState(
    run.optimizer_parameters || {},
  );
  const [editedGoalMetric, setEditedGoalMetric] = useState(
    run.goal_metric || "",
  );
  const [operationsCount, setOperationsCount] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);

  const { defaultValues: defaultOptimizerParams } = useSchema({
    modelName: editedOptimizer,
  });

  useEffect(() => {
    if (!isEditing) {
      setEditedName(run.name || "");
      setEditedParameters(run.parameters || {});
      setEditedOptimizer(run.optimizer_name || "");
      setEditedOptimizerParams(run.optimizer_parameters || {});
      setEditedGoalMetric(run.goal_metric || "");
    }
  }, [run, isEditing]);

  useEffect(() => {
    const fetchOperationsCount = async () => {
      if (!run || !run.id) return;
      try {
        const count = await getRunOperationsCount(run.id.toString());
        setOperationsCount(count);
      } catch (error) {
        console.error("Error fetching operations count:", error);
      }
    };
    fetchOperationsCount();
  }, [run.id, explainerRefreshTrigger]);

  const hasOptimizableParams = useMemo(() => {
    return Object.values(editedParameters).some(
      (value) =>
        value &&
        typeof value === "object" &&
        !Array.isArray(value) &&
        value.optimize === true,
    );
  }, [editedParameters]);

  useEffect(() => {
    if (
      editedOptimizer &&
      defaultOptimizerParams &&
      Object.keys(defaultOptimizerParams).length > 0
    ) {
      setEditedOptimizerParams((prev) => {
        if (Object.keys(prev).length === 0) {
          return defaultOptimizerParams;
        }
        return prev;
      });
    }
  }, [editedOptimizer, defaultOptimizerParams]);

  const handleStartEdit = () => {
    setIsEditing(true);
    setExpanded(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedName(run.name || "");
    setEditedParameters(run.parameters || {});
    setEditedOptimizer(run.optimizer_name || "");
    setEditedOptimizerParams(run.optimizer_parameters || {});
    setEditedGoalMetric(run.goal_metric || "");
  };

  const doSave = async () => {
    setSaveConfirmOpen(false);
    setIsSaving(true);
    try {
      await updateRunParameters(
        run.id.toString(),
        editedName.trim(),
        editedParameters,
        editedOptimizer || "",
        editedOptimizerParams || {},
        editedGoalMetric || "",
      );

      enqueueSnackbar(
        t("models:message.runUpdatedSuccess", { runName: editedName }),
        { variant: "success" },
      );

      setIsEditing(false);

      if (onRefresh) {
        await onRefresh();
      }
    } catch (error) {
      console.error("Error updating run:", error);
      enqueueSnackbar(
        t("models:error.failedToUpdateRun", {
          error: error.message || t("common:unknownError"),
        }),
        { variant: "error" },
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editedName.trim()) {
      enqueueSnackbar(t("models:error.runNameEmpty"), { variant: "warning" });
      return;
    }

    const nameExists = existingRuns.some(
      (r) =>
        r.id !== run.id &&
        r.name &&
        r.name.toLowerCase() === editedName.trim().toLowerCase(),
    );
    if (nameExists) {
      enqueueSnackbar(
        t("models:error.runNameExists", { name: editedName.trim() }),
        { variant: "error" },
      );
      return;
    }

    if (hasOptimizableParams) {
      if (!editedOptimizer) {
        enqueueSnackbar(t("models:error.selectOptimizerRequired"), {
          variant: "warning",
        });
        return;
      }
      if (!editedGoalMetric) {
        enqueueSnackbar(t("models:error.selectGoalMetricRequired"), {
          variant: "warning",
        });
        return;
      }
    }

    // If operations exist, warn before saving (they will be deleted on next train)
    if (
      operationsCount &&
      (operationsCount.explainers > 0 || operationsCount.predictions > 0)
    ) {
      setSaveConfirmOpen(true);
      return;
    }

    await doSave();
  };

  const handleParametersChange = useCallback((values) => {
    setEditedParameters(values);
  }, []);

  const handleOptimizerParamsChange = useCallback((values) => {
    setEditedOptimizerParams((prev) => ({ ...prev, ...values }));
  }, []);

  const handleOptimizerSelected = (optimizerName, defaultValues) => {
    setEditedOptimizer(optimizerName);
    if (defaultValues && Object.keys(defaultValues).length > 0) {
      setEditedOptimizerParams(defaultValues);
    }
  };

  const statusText = getRunStatus(run.status, t);
  const model = models.find((m) => m.name === run.model_name);
  const modelDisplayName = model?.display_name || run.model_name;

  const getStatusColor = (status) => {
    switch (status) {
      case 0:
        return "default";
      case 1:
      case 2:
        return "info";
      case 3:
        return "success";
      case 4:
        return "error";
      default:
        return "default";
    }
  };

  const canTrain = run.status === 0 || run.status === 3 || run.status === 4; // Not Started, Finished, Error
  const isRunning = run.status === 1 || run.status === 2; // Delivered, Started

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
          run.status === 3 // Finished
            ? "success.main"
            : run.status === 4 // Error
              ? "error.main"
              : isRunning
                ? "info.main"
                : "grey.500",
      }}
    >
      <CardContent>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
            gap: 1,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}>
            <Tooltip
              title={
                expanded
                  ? t("models:button.hideParameters")
                  : t("models:button.showParameters")
              }
            >
              <IconButton
                size="small"
                onClick={() => setExpanded(!expanded)}
                color={expanded ? "primary" : "default"}
                disabled={isEditing}
              >
                {expanded ? (
                  <ExpandLess fontSize="small" />
                ) : (
                  <ExpandMore fontSize="small" />
                )}
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

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {isEditing && (
              <>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Cancel />}
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  {t("common:cancel")}
                </Button>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<Save />}
                  onClick={handleSaveEdit}
                  disabled={isSaving}
                >
                  {isSaving ? t("common:saving") : t("common:save")}
                </Button>
              </>
            )}

            {!isEditing && run.status !== 1 && run.status !== 2 && (
              <Button
                variant="outlined"
                size="small"
                color="primary"
                startIcon={<Edit />}
                onClick={handleStartEdit}
              >
                {t("common:edit")}
              </Button>
            )}
            {canTrain && (
              <Tooltip
                title={
                  run.status === 3 &&
                  operationsCount &&
                  (operationsCount.explainers > 0 ||
                    operationsCount.predictions > 0)
                    ? t("models:message.retrainWillResetOperations", {
                        explainersCount: operationsCount.explainers,
                        predictionsCount: operationsCount.predictions,
                      })
                    : ""
                }
              >
                <Button
                  variant="contained"
                  color={
                    run.status === 3 &&
                    operationsCount &&
                    (operationsCount.explainers > 0 ||
                      operationsCount.predictions > 0)
                      ? "warning"
                      : "primary"
                  }
                  size="small"
                  startIcon={<PlayArrow />}
                  onClick={() => onTrain(run, operationsCount)}
                  data-tour={isLastRun ? "train-button" : undefined}
                  disabled={isEditing}
                >
                  {run.status === 3
                    ? t("common:retrain")
                    : t("common:trainVerb")}
                </Button>
              </Tooltip>
            )}
            {isRunning && (
              <Button
                variant="contained"
                color="warning"
                size="small"
                disabled
                startIcon={<Stop />}
              >
                {t("common:running")}
              </Button>
            )}

            <Chip
              label={statusText}
              color={getStatusColor(run.status)}
              size="small"
            />

            <Tooltip title={t("models:button.deleteRun")}>
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

        {metrics && Object.keys(metrics).length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              {t("common:metrics")}
            </Typography>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
              {Object.entries(metrics).map(([metric, values]) => {
                const avgValue =
                  values.reduce((sum, val) => sum + val, 0) / values.length;
                return (
                  <Box key={metric}>
                    <Typography
                      variant="caption"
                      sx={{ color: theme.palette.text.secondary }}
                    >
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

        {run.description && (
          <Typography
            variant="body2"
            sx={{ color: theme.palette.text.secondary, mb: 2 }}
          >
            {run.description}
          </Typography>
        )}

        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Box
            sx={{
              mt: 2,
              ...(isEditing && {
                maxHeight: "500px",
                overflowY: "auto",
                overflowX: "hidden",
                pr: 1,
              }),
            }}
          >
            {isEditing ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <Alert severity="info">
                  {t("models:message.editingParametersWarning")}
                </Alert>

                <TextField
                  label={t("models:label.runName")}
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  fullWidth
                  required
                  size="small"
                />

                {run.model_name && (
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 2 }}>
                      {t("common:modelParameters")}
                    </Typography>
                    <FormSchemaContainer>
                      <FormSchemaWithSelectedModel
                        modelToConfigure={run.model_name}
                        initialValues={editedParameters}
                        onFormSubmit={handleParametersChange}
                        onValuesChange={handleParametersChange}
                        onCancel={() => {}}
                        hideButtons
                      />
                    </FormSchemaContainer>
                  </Box>
                )}

                {hasOptimizableParams && (
                  <Box
                    sx={{ display: "flex", flexDirection: "column", gap: 2 }}
                  >
                    <Divider />
                    <Typography variant="subtitle2">
                      {t("models:label.hyperparameterOptimizerConfiguration")}
                    </Typography>
                    <Alert severity="warning" icon={false}>
                      {t("models:message.parametersMarkedForOptimization")}
                    </Alert>

                    <Box>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        {t("models:label.goalMetric")} *
                      </Typography>
                      <ModelsTableSelectMetric
                        taskName={session?.task_name}
                        metricName={editedGoalMetric}
                        handleSelectedMetric={setEditedGoalMetric}
                        required
                      />
                    </Box>

                    {/* Optimizer Selection */}
                    <OptimizationTableSelectOptimizer
                      taskName={session?.task_name}
                      optimizerName={editedOptimizer}
                      handleSelectedOptimizer={handleOptimizerSelected}
                    />

                    {editedOptimizer && (
                      <Box>
                        <Typography variant="subtitle2" sx={{ mb: 2 }}>
                          {t("common:optimizerParameters")}
                        </Typography>
                        <FormSchemaContainer>
                          <FormSchemaWithSelectedModel
                            modelToConfigure={editedOptimizer}
                            initialValues={editedOptimizerParams}
                            onFormSubmit={(values) =>
                              setEditedOptimizerParams(values)
                            }
                            onValuesChange={handleOptimizerParamsChange}
                            onCancel={() => {}}
                            hideButtons
                          />
                        </FormSchemaContainer>
                      </Box>
                    )}
                  </Box>
                )}

                <Box
                  sx={{
                    display: "flex",
                    gap: 2,
                    justifyContent: "flex-end",
                    mt: 2,
                  }}
                >
                  <Button
                    variant="outlined"
                    startIcon={<Cancel />}
                    onClick={handleCancelEdit}
                    disabled={isSaving}
                  >
                    {t("common:cancel")}
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={<Save />}
                    onClick={handleSaveEdit}
                    disabled={isSaving}
                  >
                    {isSaving ? t("common:saving") : t("common:saveChanges")}
                  </Button>
                </Box>
              </Box>
            ) : (
              <Box>
                {run.parameters && Object.keys(run.parameters).length > 0 && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      {t("common:modelParameters")}
                    </Typography>
                    <TableContainer component={Paper}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>{t("common:parameter")}</TableCell>
                            <TableCell>{t("common:value")}</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {Object.entries(run.parameters).map(
                            ([key, value]) => (
                              <TableRow key={key}>
                                <TableCell>{key}</TableCell>
                                <TableCell>{renderParamValue(value)}</TableCell>
                              </TableRow>
                            ),
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                )}

                {run.optimizer_name && run.goal_metric && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      {t("common:optimizer")}: {run.optimizer_name}
                    </Typography>
                    {run.optimizer_parameters &&
                      Object.keys(run.optimizer_parameters).length > 0 && (
                        <TableContainer component={Paper}>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>{t("common:parameter")}</TableCell>
                                <TableCell>{t("common:value")}</TableCell>
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

                {run.goal_metric && (
                  <Box sx={{ mt: 2 }}>
                    <Typography
                      variant="body2"
                      sx={{ color: theme.palette.text.secondary }}
                    >
                      {t("models:label.goalMetric")}:{" "}
                      <strong>{run.goal_metric}</strong>
                    </Typography>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        </Collapse>

        <Box sx={{ mt: 2 }}>
          <RunResults
            run={run}
            session={session}
            onRefresh={onOperationsRefresh}
            explainerRefreshTrigger={explainerRefreshTrigger}
          />
        </Box>
        <RetrainConfirmDialog
          mode="save"
          open={saveConfirmOpen}
          onClose={() => setSaveConfirmOpen(false)}
          onConfirm={doSave}
          run={run}
          operationsCount={operationsCount}
        />
      </CardContent>
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
    model_session_id: PropTypes.number,
  }).isRequired,
  models: PropTypes.array,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onTrain: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onOperationsRefresh: PropTypes.func,
  explainerRefreshTrigger: PropTypes.number,
  isLastRun: PropTypes.bool,
  existingRuns: PropTypes.array,
  onRefresh: PropTypes.func,
};

export default RunCard;
