import React, { useState, useEffect, useMemo } from "react";
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
  MenuItem,
  Box,
  IconButton,
  Typography,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import FormSchemaWithSelectedModel from "../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../shared/FormSchemaContainer";
import OptimizationTableSelectOptimizer from "../experiments/OptimizationTableSelectOptimizer";
import useSchema from "../../hooks/useSchema";
import { generateSequentialName } from "../../utils/nameGenerator";
import { createRun } from "../../api/run";
import { getComponents } from "../../api/component";

/**
 * Dialog for adding a new model run to a session
 * Step 1: Configure model name and parameters
 * Step 2: Configure optimizer
 */
function AddModelDialog({
  open,
  onClose,
  session,
  preselectedModel,
  existingRuns = [],
  onRunCreated,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [activeStep, setActiveStep] = useState(0);
  const [name, setName] = useState("");
  const [selectedModel, setSelectedModel] = useState(preselectedModel || "");
  const [modelParameters, setModelParameters] = useState({});
  const [selectedOptimizer, setSelectedOptimizer] = useState("OptunaOptimizer");
  const [optimizerParameters, setOptimizerParameters] = useState({
    n_trials: 10,
    sampler: "TPESampler",
    pruner: "None",
  });
  const [compatibleModels, setCompatibleModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasUserTouchedName, setHasUserTouchedName] = useState(false);

  const { defaultValues: defaultModelParams } = useSchema({
    modelName: selectedModel,
  });
  const { defaultValues: defaultOptimizerParams } = useSchema({
    modelName: selectedOptimizer,
  });

  const steps = ["Configure Model", "Configure Optimizer"];

  // Generate default name
  const { defaultName } = useMemo(() => {
    if (!selectedModel) {
      return { defaultName: "" };
    }

    return generateSequentialName({
      base: selectedModel,
      items: existingRuns,
      getName: (run) => run.name,
      filter: (run) => run.model_name === selectedModel,
    });
  }, [selectedModel, existingRuns]);

  // Fetch compatible models when dialog opens
  useEffect(() => {
    if (open && session?.task_name) {
      const fetchModels = async () => {
        try {
          const models = await getComponents({
            selectTypes: ["Model"],
            relatedComponent: session.task_name,
          });
          setCompatibleModels(models);
        } catch (error) {
          console.error("Error fetching models:", error);
          enqueueSnackbar("Error fetching compatible models", {
            variant: "error",
          });
        }
      };
      fetchModels();
    } else if (!open) {
      // Reset models when dialog closes
      setCompatibleModels([]);
    }
  }, [open, session?.task_name, enqueueSnackbar]);

  // Set preselected model if provided
  useEffect(() => {
    if (preselectedModel && preselectedModel !== selectedModel) {
      setSelectedModel(preselectedModel);
    }
  }, [preselectedModel, selectedModel]);

  // Update default name when model changes
  useEffect(() => {
    if (defaultName && !hasUserTouchedName) {
      setName(defaultName);
    }
  }, [defaultName, hasUserTouchedName]);

  // Set default model parameters when model is selected
  useEffect(() => {
    if (defaultModelParams && Object.keys(defaultModelParams).length > 0) {
      setModelParameters((prev) => {
        // Only update if params have actually changed
        const prevKeys = Object.keys(prev).sort().join(",");
        const newKeys = Object.keys(defaultModelParams).sort().join(",");
        if (
          prevKeys === newKeys &&
          JSON.stringify(prev) === JSON.stringify(defaultModelParams)
        ) {
          return prev;
        }
        return defaultModelParams;
      });
    }
  }, [defaultModelParams]);

  // Set default optimizer parameters when optimizer is selected
  useEffect(() => {
    if (
      defaultOptimizerParams &&
      Object.keys(defaultOptimizerParams).length > 0
    ) {
      setOptimizerParameters((prev) => {
        // Only update if params have actually changed
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
  }, [defaultOptimizerParams]);

  const handleClose = () => {
    setActiveStep(0);
    setName("");
    setSelectedModel(preselectedModel || "");
    setModelParameters({});
    setSelectedOptimizer("OptunaOptimizer");
    setOptimizerParameters({
      n_trials: 10,
      sampler: "TPESampler",
      pruner: "None",
    });
    setHasUserTouchedName(false);
    onClose();
  };

  const handleNext = () => {
    if (activeStep === 0) {
      // Validate step 1
      if (!selectedModel || name.trim() === "") {
        enqueueSnackbar("Please select a model and enter a name", {
          variant: "warning",
        });
        return;
      }

      // Check for duplicate names
      const nameExists = existingRuns.some(
        (run) =>
          run.name && run.name.toLowerCase() === name.trim().toLowerCase(),
      );
      if (nameExists) {
        enqueueSnackbar("A run with this name already exists", {
          variant: "error",
        });
        return;
      }

      setActiveStep(1);
    } else {
      // Step 2: Create the run
      handleCreateRun();
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleCreateRun = async () => {
    try {
      setLoading(true);

      const newRun = await createRun(
        session.id.toString(),
        selectedModel,
        name.trim(),
        modelParameters,
        selectedOptimizer,
        optimizerParameters,
        "", // plot_history_path
        "", // plot_slice_path
        "", // plot_contour_path
        "", // plot_importance_path
        "", // goal_metric (can be set later)
        "", // description
      );

      enqueueSnackbar(`Run "${name}" created successfully`, {
        variant: "success",
      });

      if (onRunCreated) {
        onRunCreated(newRun);
      }

      handleClose();
    } catch (error) {
      console.error("Error creating run:", error);
      enqueueSnackbar("Error creating run", { variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleModelParametersSubmit = (values) => {
    setModelParameters(values);
  };

  const handleOptimizerSelected = (optimizerName, defaultValues) => {
    setSelectedOptimizer(optimizerName);
    if (defaultValues && Object.keys(defaultValues).length > 0) {
      setOptimizerParameters(defaultValues);
    }
  };

  const isStep1Valid = selectedModel && name.trim() !== "";
  const isStep2Valid = selectedOptimizer && optimizerParameters;

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
          Add Model to Session
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
              select
              label="Select Model"
              value={selectedModel}
              onChange={(e) => {
                setSelectedModel(e.target.value);
                setHasUserTouchedName(false);
              }}
              fullWidth
              required
            >
              {compatibleModels.length === 0 && (
                <MenuItem value="" disabled>
                  No models available
                </MenuItem>
              )}
              {compatibleModels.map((model) => (
                <MenuItem key={model.name} value={model.name}>
                  {model.display_name || model.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Run Name"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setHasUserTouchedName(true);
              }}
              fullWidth
              required
              disabled={!selectedModel}
              placeholder={!selectedModel ? "Select a model first" : "Run Name"}
            />

            {selectedModel && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 2 }}>
                  Model Parameters
                </Typography>
                <FormSchemaContainer>
                  <FormSchemaWithSelectedModel
                    modelToConfigure={selectedModel}
                    initialValues={modelParameters}
                    onFormSubmit={handleModelParametersSubmit}
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
          {activeStep === steps.length - 1 ? "Create Run" : "Next"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

AddModelDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  preselectedModel: PropTypes.string,
  existingRuns: PropTypes.array,
  onRunCreated: PropTypes.func,
};

export default AddModelDialog;
