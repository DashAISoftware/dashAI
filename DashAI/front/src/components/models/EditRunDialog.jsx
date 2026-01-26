import React, { useState, useEffect, useMemo, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stepper,
  Step,
  StepLabel,
  TextField,
  Box,
  IconButton,
  Typography,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import FormSchemaWithSelectedModel from "../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../shared/FormSchemaContainer";
import OptimizationTableSelectOptimizer from "../experiments/OptimizationTableSelectOptimizer";
import ModelsTableSelectMetric from "../experiments/ModelsTableSelectMetric";
import useSchema from "../../hooks/useSchema";

/**
 * Dialog for editing an existing model run parameters
 * Step 1: Configure model name and parameters
 * Step 2: Configure optimizer (if optimizable parameters exist)
 */
function EditRunDialog({
  open,
  onClose,
  session,
  run,
  existingRuns = [],
  onRunUpdated,
  onConfirmEdit,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [activeStep, setActiveStep] = useState(0);
  const [name, setName] = useState("");
  const [modelParameters, setModelParameters] = useState({});
  const [selectedOptimizer, setSelectedOptimizer] = useState("");
  const [optimizerParameters, setOptimizerParameters] = useState({});
  const [loading, setLoading] = useState(false);
  const [hasUserTouchedName, setHasUserTouchedName] = useState(false);
  const [goalMetric, setGoalMetric] = useState("");
  const [hasLoadedInitialParams, setHasLoadedInitialParams] = useState(false);

  const { defaultValues: defaultOptimizerParams } = useSchema({
    modelName: selectedOptimizer,
  });

  // Initialize form with existing run data
  useEffect(() => {
    if (open && run) {
      setName(run.name || "");
      setModelParameters(run.parameters || {});
      setSelectedOptimizer(run.optimizer_name || "");
      setOptimizerParameters(run.optimizer_parameters || {});
      setGoalMetric(run.goal_metric || "");
      setHasLoadedInitialParams(true);
      setHasUserTouchedName(false);
      setActiveStep(0);
    }
  }, [open, run]);

  const hasOptimizableParams = useMemo(() => {
    return Object.values(modelParameters).some(
      (value) =>
        value &&
        typeof value === "object" &&
        !Array.isArray(value) &&
        value.optimize === true,
    );
  }, [modelParameters]);

  const steps = hasOptimizableParams
    ? ["Configure Model", "Configure Optimizer"]
    : ["Configure Model"];

  const handleModelParametersChange = useCallback((values) => {
    setModelParameters(values);
  }, []);

  const handleOptimizerParametersChange = useCallback((values) => {
    setOptimizerParameters((prevParams) => ({ ...prevParams, ...values }));
  }, []);

  useEffect(() => {
    if (
      defaultOptimizerParams &&
      Object.keys(defaultOptimizerParams).length > 0 &&
      !hasLoadedInitialParams
    ) {
      setOptimizerParameters((prev) => {
        const prevKeys = Object.keys(prev).sort().join(",");
        const newKeys = Object.keys(defaultOptimizerParams).sort().join(",");
        if (
          prevKeys === newKeys &&
          JSON.stringify(prev) === JSON.stringify(defaultOptimizerParams)
        ) {
          return prev;
        }
        return defaultOptimizerParams;
      });
    }
  }, [defaultOptimizerParams, hasLoadedInitialParams]);

  const handleClose = () => {
    setTimeout(() => {
      setActiveStep(0);
      setName("");
      setModelParameters({});
      setSelectedOptimizer("");
      setOptimizerParameters({});
      setGoalMetric("");
      setHasUserTouchedName(false);
      setHasLoadedInitialParams(false);
    }, 100);
    onClose();
  };

  const handleNext = () => {
    if (activeStep === 0) {
      if (name.trim() === "") {
        enqueueSnackbar("Please enter a name for the model", {
          variant: "warning",
        });
        return;
      }

      // Check for duplicate names (excluding current run)
      const nameExists = existingRuns.some(
        (r) =>
          r.id !== run.id &&
          r.name &&
          r.name.toLowerCase() === name.trim().toLowerCase(),
      );
      if (nameExists) {
        enqueueSnackbar("A run with this name already exists", {
          variant: "error",
        });
        return;
      }

      if (hasOptimizableParams) {
        setActiveStep(1);
      } else {
        handleConfirmUpdate();
      }
    } else {
      handleConfirmUpdate();
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleConfirmUpdate = () => {
    if (onConfirmEdit) {
      // Pass the updated data to the confirmation dialog
      onConfirmEdit({
        runId: run.id,
        name: name.trim(),
        parameters: modelParameters,
        optimizer: selectedOptimizer || "",
        optimizer_parameters: optimizerParameters || {},
        goal_metric: goalMetric || "",
      });
    }
    handleClose();
  };

  const handleOptimizerSelected = (optimizerName, defaultValues) => {
    setSelectedOptimizer(optimizerName);
    if (defaultValues && Object.keys(defaultValues).length > 0) {
      setOptimizerParameters(defaultValues);
    }
  };

  const isStep1Valid = Boolean(run?.model_name && name.trim() !== "");
  const isStep2Valid = Boolean(
    selectedOptimizer &&
      optimizerParameters &&
      Object.keys(optimizerParameters).length > 0 &&
      goalMetric,
  );

  if (!run) {
    return null;
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: "500px" },
      }}
    >
      <DialogTitle>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          Edit Model Parameters
          <IconButton
            onClick={handleClose}
            size="small"
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {activeStep === 0 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <TextField
              label="Model Name"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setHasUserTouchedName(true);
              }}
              fullWidth
              required
              placeholder="Model Name"
              helperText={run.model_name ? `Model: ${run.model_name}` : ""}
            />

            {run.model_name && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 2 }}>
                  Model Parameters
                </Typography>
                <FormSchemaContainer key={run.model_name}>
                  <FormSchemaWithSelectedModel
                    modelToConfigure={run.model_name}
                    initialValues={modelParameters}
                    onFormSubmit={handleModelParametersChange}
                    onValuesChange={handleModelParametersChange}
                    onCancel={() => {}}
                    hideButtons
                  />
                </FormSchemaContainer>
              </Box>
            )}
          </Box>
        )}

        {activeStep === 1 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="subtitle2">
              Configure Hyperparameter Optimizer
            </Typography>

            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                Goal Metric *
              </Typography>
              <ModelsTableSelectMetric
                taskName={session?.task_name}
                metricName={goalMetric}
                handleSelectedMetric={setGoalMetric}
                required
              />
            </Box>

            <OptimizationTableSelectOptimizer
              taskName={session?.task_name}
              optimizerName={selectedOptimizer}
              handleSelectedOptimizer={handleOptimizerSelected}
            />

            {selectedOptimizer && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 2 }}>
                  Optimizer Parameters
                </Typography>
                <FormSchemaContainer>
                  <FormSchemaWithSelectedModel
                    modelToConfigure={selectedOptimizer}
                    initialValues={optimizerParameters}
                    onFormSubmit={(values) => setOptimizerParameters(values)}
                    onValuesChange={handleOptimizerParametersChange}
                    onCancel={() => {}}
                    hideButtons
                  />
                </FormSchemaContainer>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        {activeStep > 0 && (
          <Button onClick={handleBack} disabled={loading}>
            Back
          </Button>
        )}
        <Button
          onClick={handleNext}
          variant="contained"
          disabled={
            loading ||
            (activeStep === 0 && !isStep1Valid) ||
            (activeStep === 1 && !isStep2Valid)
          }
        >
          {activeStep === steps.length - 1 ? "Update & Retrain" : "Next"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

EditRunDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    model_name: PropTypes.string,
    parameters: PropTypes.object,
    optimizer_name: PropTypes.string,
    optimizer_parameters: PropTypes.object,
    goal_metric: PropTypes.string,
  }),
  existingRuns: PropTypes.array,
  onRunUpdated: PropTypes.func,
  onConfirmEdit: PropTypes.func,
};

export default EditRunDialog;
