import React, { useState, useEffect, useMemo, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Button,
  Divider,
  TextField,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
} from "@mui/material";
import { Save, Cancel, Close as CloseIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import FormSchemaWithSelectedModel from "../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../shared/FormSchemaContainer";
import OptimizationTableSelectOptimizer from "./modelSession/OptimizationTableSelectOptimizer";
import ModelsTableSelectMetric from "./modelSession/ModelsTableSelectMetric";
import useSchema from "../../hooks/useSchema";
import { updateRunParameters, getRunOperationsCount } from "../../api/run";
import RetrainConfirmDialog from "./RetrainConfirmDialog";
import { checkIfHaveOptimazers } from "../../utils/schema";

/**
 * Editable-parameters dialog for a run — the same form used to configure it
 * before training, pre-filled with its current values. Shared by RunCard's
 * "Editar" button and the compact model card's quick-edit action so both
 * entry points open the exact same modal.
 */
export default function RunEditDialog({
  run,
  session,
  existingRuns = [],
  onRefresh,
  open,
  onClose,
}) {
  const { t } = useTranslation(["models", "common"]);
  const { enqueueSnackbar } = useSnackbar();

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
    modelName: open ? editedOptimizer : null,
  });

  useEffect(() => {
    if (!open) return;
    setEditedName(run.name || "");
    setEditedParameters(run.parameters || {});
    setEditedOptimizer(run.optimizer_name || "");
    setEditedOptimizerParams(run.optimizer_parameters || {});
    setEditedGoalMetric(run.goal_metric || "");
  }, [run, open]);

  const runId = run.id;
  useEffect(() => {
    if (!open || !runId) return;
    getRunOperationsCount(runId.toString())
      .then(setOperationsCount)
      .catch((error) =>
        console.error("Error fetching operations count:", error),
      );
  }, [open, runId]);

  const hasOptimizableParams = useMemo(
    () => checkIfHaveOptimazers(editedParameters),
    [editedParameters],
  );

  const doSave = async () => {
    setSaveConfirmOpen(false);
    setIsSaving(true);
    try {
      await updateRunParameters(
        run.id.toString(),
        editedName.trim(),
        editedParameters,
        editedOptimizer || "",
        { ...defaultOptimizerParams, ...editedOptimizerParams },
        editedGoalMetric || "",
      );

      enqueueSnackbar(
        t("models:message.runUpdatedSuccess", { runName: editedName }),
        { variant: "success" },
      );

      onClose();
      if (onRefresh) await onRefresh();
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
    setEditedOptimizerParams(values);
  }, []);

  const handleOptimizerSelected = (optimizerName) => {
    setEditedOptimizer(optimizerName);
    setEditedOptimizerParams({});
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { minHeight: "500px" } }}
      >
        <DialogTitle sx={{ bgcolor: "background.paper" }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="h6" component="span">
              {t("models:label.editRun")}
            </Typography>
            <IconButton
              size="small"
              onClick={onClose}
              sx={{ color: "text.secondary" }}
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
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
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
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
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
          <Button
            variant="outlined"
            startIcon={<Cancel />}
            onClick={onClose}
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
            {isSaving ? t("common:saving") : t("common:save")}
          </Button>
        </DialogActions>
      </Dialog>

      <RetrainConfirmDialog
        mode="save"
        open={saveConfirmOpen}
        onClose={() => setSaveConfirmOpen(false)}
        onConfirm={doSave}
        run={run}
        operationsCount={operationsCount}
      />
    </>
  );
}

RunEditDialog.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    model_name: PropTypes.string,
    parameters: PropTypes.object,
    optimizer_name: PropTypes.string,
    optimizer_parameters: PropTypes.object,
    goal_metric: PropTypes.string,
  }).isRequired,
  session: PropTypes.shape({
    task_name: PropTypes.string,
  }),
  existingRuns: PropTypes.array,
  onRefresh: PropTypes.func,
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};
