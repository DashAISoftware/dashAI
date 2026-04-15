import React, { useState, useEffect, useMemo, useCallback, use } from "react";
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
import OptimizationTableSelectOptimizer from "./modelSession/OptimizationTableSelectOptimizer";
import ModelsTableSelectMetric from "./modelSession/ModelsTableSelectMetric";
import useSchema from "../../hooks/useSchema";
import { generateSequentialName } from "../../utils/nameGenerator";
import { createRun } from "../../api/run";
import { useTranslation } from "react-i18next";
import { useTourContext } from "../tour/TourProvider";
import { checkIfHaveOptimazers } from "../../utils/schema";

/**
 * Dialog for adding a new model run to a session
 * Step 1: Configure model name and parameters
 * Step 2: Configure optimizer for train
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
  const [optimizerParameters, setOptimizerParameters] = useState({});
  const [loading, setLoading] = useState(false);
  const [hasUserTouchedName, setHasUserTouchedName] = useState(false);
  const [goalMetric, setGoalMetric] = useState("");
  const [hasLoadedInitialParams, setHasLoadedInitialParams] = useState(false);
  const { t } = useTranslation(["models", "common"]);

  const { defaultValues: defaultModelParams } = useSchema({
    modelName: selectedModel,
  });
  const {
    defaultValues: defaultOptimizerParams,
    loading: optimizerSchemaLoading,
  } = useSchema({
    modelName: selectedOptimizer,
  });

  const tourContext = useTourContext();

  useEffect(() => {
    if (open && selectedModel) {
      const generated = generateSequentialName({
        base: selectedModel,
        items: existingRuns,
        getName: (run) => run.name,
        filter: (run) => run.model_name === selectedModel,
      });
      if (!hasUserTouchedName) {
        setName(generated.defaultName);
      }
    }
  }, [open, selectedModel, existingRuns, hasUserTouchedName]);

  const hasOptimizableParams = useMemo(() => {
    return checkIfHaveOptimazers(modelParameters);
  }, [modelParameters]);

  const steps = hasOptimizableParams
    ? [t("models:label.configureModel"), t("models:label.configureOptimizer")]
    : [t("models:label.configureModel")];

  const handleModelParametersChange = useCallback((values) => {
    setModelParameters(values);
  }, []);

  const handleOptimizerParametersChange = useCallback((values) => {
    setOptimizerParameters((prevParams) => ({ ...prevParams, ...values }));
  }, []);

  useEffect(() => {
    if (preselectedModel && preselectedModel !== selectedModel) {
      setSelectedModel(preselectedModel);
      setModelParameters({});
      setHasUserTouchedName(false);
      setHasLoadedInitialParams(false);
    }
  }, [preselectedModel, selectedModel]);

  useEffect(() => {
    if (
      selectedModel &&
      defaultModelParams &&
      Object.keys(defaultModelParams).length > 0 &&
      !hasLoadedInitialParams
    ) {
      setModelParameters(defaultModelParams);
      setHasLoadedInitialParams(true);
    }
  }, [selectedModel, defaultModelParams, hasLoadedInitialParams]);

  useEffect(() => {
    if (
      !optimizerSchemaLoading &&
      defaultOptimizerParams &&
      Object.keys(defaultOptimizerParams).length > 0
    ) {
      setOptimizerParameters(defaultOptimizerParams);
    }
  }, [selectedOptimizer, optimizerSchemaLoading]);

  const handleClose = () => {
    setTimeout(() => {
      setActiveStep(0);
      setName("");
      setSelectedModel("");
      setModelParameters({});
      setSelectedOptimizer("OptunaOptimizer");
      setOptimizerParameters({});
      setGoalMetric("");
      setHasUserTouchedName(false);
      setHasLoadedInitialParams(false);
    }, 100);
    onClose();
  };

  const handleNext = () => {
    if (activeStep === 0) {
      if (!selectedModel) {
        enqueueSnackbar(t("models:error.noModelSelected"), {
          variant: "error",
        });
        handleClose();
        return;
      }

      if (name.trim() === "") {
        enqueueSnackbar(t("models:error.enterModelName"), {
          variant: "warning",
        });
        return;
      }

      const nameExists = existingRuns.some(
        (run) =>
          run.name && run.name.toLowerCase() === name.trim().toLowerCase(),
      );
      if (nameExists) {
        enqueueSnackbar(t("models:error.runNameExists", { name }), {
          variant: "error",
        });
        return;
      }

      if (hasOptimizableParams) {
        setActiveStep(1);
      } else {
        handleCreateRun();
      }
    } else {
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
        modelParameters || {},
        selectedOptimizer || "",
        optimizerParameters || {},
        "",
        "",
        "",
        "",
        goalMetric || "",
        "",
      );

      enqueueSnackbar(t("models:message.runCreatedSuccess", { name }), {
        variant: "success",
      });

      let shouldDelayClose = false;
      if (onRunCreated) {
        onRunCreated(newRun);
      }

      if (tourContext?.run && tourContext?.stepIndex === 3) {
        shouldDelayClose = true;
        setTimeout(() => {
          const runCard = document.querySelector(
            '[data-tour="first-run-card"]',
          );
          if (runCard) {
            runCard.scrollIntoView({
              behavior: "smooth",
              block: "center",
              inline: "nearest",
            });
          }
          setTimeout(() => {
            tourContext.nextStep();
            handleClose();
          }, 100);
        }, 100);
      }
      if (!shouldDelayClose) {
        handleClose();
      }
    } catch (error) {
      console.error("Error creating run:", error);

      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }

      enqueueSnackbar(t("models:error.createRun", { name }), {
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleOptimizerSelected = (optimizerName) => {
    setOptimizerParameters({});
    setSelectedOptimizer(optimizerName);
  };

  const isStep1Valid = Boolean(selectedModel && name.trim() !== "");
  const isStep2Valid = Boolean(selectedOptimizer && goalMetric);

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
          {t("models:label.addModelToSession")}
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
              label={t("common:modelName")}
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setHasUserTouchedName(true);
              }}
              fullWidth
              required
              placeholder={t("common:modelName")}
              helperText={selectedModel ? `Model: ${selectedModel}` : ""}
            />

            {selectedModel && (
              <Box data-tour="model-config">
                <Typography variant="subtitle2" sx={{ mb: 2 }}>
                  {t("common:modelParameters")}
                </Typography>
                <FormSchemaContainer key={selectedModel}>
                  <FormSchemaWithSelectedModel
                    modelToConfigure={selectedModel}
                    initialValues={modelParameters}
                    onFormSubmit={() => {}}
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
              {t("models:label.optimizerConfiguration")}
            </Typography>

            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {t("models:label.goalMetric")} *
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
                  {t("models:label.optimizerParameters")}
                </Typography>
                <FormSchemaContainer key={selectedOptimizer}>
                  <FormSchemaWithSelectedModel
                    modelToConfigure={selectedOptimizer}
                    initialValues={optimizerParameters}
                    onFormSubmit={() => {}}
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
          {t("common:cancel")}
        </Button>
        {activeStep > 0 && (
          <Button onClick={handleBack} disabled={loading}>
            {t("common:back")}
          </Button>
        )}
        <Button
          data-tour="add-model-button"
          onClick={handleNext}
          variant="contained"
          disabled={
            loading ||
            (activeStep === 0 && !isStep1Valid) ||
            (activeStep === 1 && !isStep2Valid)
          }
        >
          {activeStep === steps.length - 1
            ? t("common:addModel")
            : t("common:next")}
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
