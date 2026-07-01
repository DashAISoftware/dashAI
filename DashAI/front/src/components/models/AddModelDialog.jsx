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
  Box,
  IconButton,
  Tooltip,
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
import ComponentDownloadControl from "./model/ComponentDownloadControl";

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
  preselectedModelObject,
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
  const [modelDownloaded, setModelDownloaded] = useState(true);
  const { t } = useTranslation(["models", "common"]);

  const { defaultValues: defaultModelParams } = useSchema({
    modelName: open ? selectedModel : null,
  });
  const {
    defaultValues: defaultOptimizerParams,
    loading: optimizerSchemaLoading,
  } = useSchema({
    modelName: open && activeStep === 1 ? selectedOptimizer : null,
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

  useEffect(() => {
    if (preselectedModel && preselectedModel !== selectedModel) {
      setSelectedModel(preselectedModel);
      setModelParameters({});
      setHasUserTouchedName(false);
      setHasLoadedInitialParams(false);
    }
  }, [preselectedModel, selectedModel]);

  useEffect(() => {
    const comp = preselectedModelObject;
    const requiresDownload = Boolean(comp?.metadata?.requires_download);
    const isDownloaded = Boolean(comp?.downloaded);
    setModelDownloaded(!requiresDownload || isDownloaded);
  }, [preselectedModelObject]);

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
        { ...defaultOptimizerParams, ...optimizerParameters },
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
      <DialogTitle sx={{ bgcolor: "background.paper" }}>
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

      <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
        <Stepper activeStep={activeStep} sx={{ mb: 6 }}>
          {steps.map((label) => (
            <Step key={label} completed={false}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {activeStep === 0 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 6 }}>
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
                <Typography variant="subtitle2" sx={{ mb: 4 }}>
                  {t("common:modelParameters")}
                </Typography>
                <FormSchemaContainer key={selectedModel}>
                  <FormSchemaWithSelectedModel
                    modelToConfigure={selectedModel}
                    initialValues={modelParameters}
                    onFormSubmit={() => {}}
                    onValuesChange={setModelParameters}
                    onCancel={() => {}}
                    hideButtons
                  />
                </FormSchemaContainer>
              </Box>
            )}
            {preselectedModelObject?.metadata?.requires_download && (
              <ComponentDownloadControl
                component={preselectedModelObject}
                onStatusChange={setModelDownloaded}
              />
            )}
          </Box>
        )}

        {activeStep === 1 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <Typography variant="subtitle2">
              {t("models:label.optimizerConfiguration")}
            </Typography>

            <Box>
              <Typography variant="body2" sx={{ mb: 2 }}>
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

            {selectedOptimizer && !optimizerSchemaLoading && (
              <Box sx={{ mt: 4 }}>
                <Typography variant="subtitle2" sx={{ mb: 4 }}>
                  {t("models:label.optimizerParameters")}
                </Typography>
                <FormSchemaContainer key={selectedOptimizer}>
                  <FormSchemaWithSelectedModel
                    modelToConfigure={selectedOptimizer}
                    initialValues={defaultOptimizerParams}
                    onFormSubmit={() => {}}
                    onValuesChange={setOptimizerParameters}
                    onCancel={() => {}}
                    hideButtons
                  />
                </FormSchemaContainer>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 4, bgcolor: "background.paper" }}>
        <Button variant="outlined" onClick={handleClose} disabled={loading}>
          {t("common:cancel")}
        </Button>
        {activeStep > 0 && (
          <Button variant="outlined" onClick={handleBack} disabled={loading}>
            {t("common:back")}
          </Button>
        )}
        <Tooltip
          title={
            activeStep === 0 &&
            preselectedModelObject?.metadata?.requires_download &&
            !modelDownloaded
              ? t("common:componentDownload.mustDownload")
              : ""
          }
        >
          <span>
            <Button
              data-tour="add-model-button"
              onClick={handleNext}
              variant="contained"
              disabled={
                loading ||
                (activeStep === 0 && !isStep1Valid) ||
                (activeStep === 1 && !isStep2Valid) ||
                (activeStep === 0 &&
                  Boolean(
                    preselectedModelObject?.metadata?.requires_download,
                  ) &&
                  !modelDownloaded)
              }
            >
              {activeStep === steps.length - 1
                ? t("common:addModel")
                : t("common:next")}
            </Button>
          </span>
        </Tooltip>
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
  preselectedModelObject: PropTypes.object,
  existingRuns: PropTypes.array,
  onRunCreated: PropTypes.func,
};

export default AddModelDialog;
