import React, { useState, useMemo, use, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  ButtonGroup,
  Stepper,
  Step,
  StepButton,
  Grid,
  Typography,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useSnackbar } from "notistack";

import { createModelSession as createModelSessionRequest } from "../../api/modelSession";
import { createRun as createRunRequest } from "../../api/run";
import { generateSequentialName } from "../../utils/nameGenerator";
import { checkIfHaveOptimazers } from "../../utils/schema";
import { TIMESTAMP_KEYS } from "../../constants/timestamp";
import TimestampWrapper from "../shared/TimestampWrapper";
import { useTourContext } from "../tour/TourProvider";
import { renderStep } from "./renderStep";
import { useTranslation } from "react-i18next";

const EMPTY_ARRAY = [];

export default function NewExperimentModal({
  open,
  setOpen,
  updateExperiments,
  preselectedDataset,
  setPreselectedDataset,
  existingExperiments = EMPTY_ARRAY,
}) {
  const theme = useTheme();
  const matches = useMediaQuery(theme.breakpoints.down("md"));
  const screenSm = useMediaQuery(theme.breakpoints.down("sm"));
  const tourContext = useTourContext();
  const { t } = useTranslation(["experiments", "common"]);

  const defaultNewExp = useMemo(
    () => ({
      id: "",
      name: "",
      dataset: preselectedDataset,
      task_name: "",
      input_columns: [],
      output_columns: [],
      train_metrics: [],
      validation_metrics: [],
      test_metrics: [],
      splits: {
        train: 0.6,
        validation: 0.2,
        test: 0.2,
      },
      step: "SET_NAME",
      created: null,
      last_modified: null,
      runs: [],
    }),
    [preselectedDataset],
  );

  // Build steps dynamically
  const steps = [
    { name: "selectTask", label: t("experiments:label.setNameAndTask") },
    ...(preselectedDataset
      ? []
      : [
          {
            name: "selectDataset",
            label: t("experiments:label.selectDataset"),
          },
        ]),
    { name: "prepareDataset", label: t("experiments:label.prepareDataset") },
    { name: "metricsSelection", label: t("experiments:label.selectMetrics") },
    { name: "configureModels", label: t("experiments:label.configureModels") },
    {
      name: "configureOptimizer",
      label: t("experiments:label.configureOptimizer"),
    },
  ];

  const { enqueueSnackbar } = useSnackbar();

  const [activeStep, setActiveStep] = useState(0);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [newExp, setNewExp] = useState(defaultNewExp);
  const [defaultName, setDefaultName] = useState(
    generateSequentialName({
      base: "Experiment",
      items: existingExperiments,
    }).defaultName,
  );

  useEffect(() => {
    if (open) {
      const generatedName = generateSequentialName({
        base: "Experiment",
        items: existingExperiments,
      });
      setDefaultName(generatedName.defaultName);
    }
  }, [open, existingExperiments]);

  const uploadRuns = async (experimentId) => {
    for (const run of newExp.runs) {
      try {
        await createRunRequest(
          experimentId,
          run.model,
          run.name,
          run.params,
          run.optimizer_name || "",
          run.optimizer_parameters || {},
          run.plot_history_path || "",
          run.plot_slice_path || "",
          run.plot_contour_path || "",
          run.plot_importance_path || "",
          run.goal_metric || "",
          "",
        );
      } catch (error) {
        enqueueSnackbar(
          t("experiments:error.errorCreatingRun", { runName: run.name }),
        );

        if (error.response) {
          console.error("Response error:", error.message);
        } else if (error.request) {
          console.error("Request error", error.request);
        } else {
          console.error("Unknown Error", error.message);
        }
      } finally {
        setPreselectedDataset(null);
      }
    }
  };

  const uploadNewExperiment = async () => {
    try {
      const finalExperimentName =
        newExp.name.trim() === "" ? defaultName : newExp.name.trim();

      const response = await createModelSessionRequest(
        newExp.dataset.id,
        newExp.task_name,
        finalExperimentName,
        newExp.input_columns,
        newExp.output_columns,
        newExp.train_metrics,
        newExp.validation_metrics,
        newExp.test_metrics,
        JSON.stringify(newExp.splits),
      );
      const experimentId = response.id;
      await uploadRuns(experimentId);

      enqueueSnackbar(t("experiments:message.experimentCreatedSuccessfully"), {
        variant: "success",
      });
      updateExperiments();
    } catch (error) {
      enqueueSnackbar(t("experiments:error.errorCreatingExperiment"));

      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };
  const handleCloseDialog = () => {
    setActiveStep(0);
    setOpen(false);
    setNewExp(defaultNewExp);
    setPreselectedDataset(null);
    setNextEnabled(false);
  };

  const handleStepButton = (stepIndex) => () => {
    setActiveStep(stepIndex);
  };

  const handleBackButton = () => {
    if (activeStep === 0) {
      handleCloseDialog();
    } else {
      setActiveStep((prev) => prev - 1);
    }
  };

  const handleNextButton = () => {
    if (activeStep === steps.length - 1) {
      uploadNewExperiment();
      handleCloseDialog();
      if (tourContext && tourContext.run) {
        setTimeout(() => {
          tourContext.nextStep();
        }, 500);
      }
      return;
    }

    if (steps[activeStep].name === "configureModels") {
      const haveOptimazers = newExp.runs.some(checkIfHaveOptimazers);

      if (!haveOptimazers) {
        uploadNewExperiment();
        setOpen(false);
        setTimeout(() => {
          setActiveStep(0);
          setNewExp(defaultNewExp);
          setNextEnabled(false);
        }, 100);
        if (tourContext && tourContext.run) {
          setTimeout(() => {
            tourContext.nextStep();
          }, 600);
        }
        return;
      }
    }

    setActiveStep((prevStep) => prevStep + 1);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 300);
    }
    setNextEnabled(false);
  };

  useEffect(() => {
    if (steps[activeStep].name === "configureModels") {
      const allModelsHaveMetric = newExp.runs.every((model) => {
        if (checkIfHaveOptimazers(model)) {
          return model.goal_metric;
        }
        return true;
      });
      if (newExp.runs.length && allModelsHaveMetric) {
        setNextEnabled(true);
      } else {
        setNextEnabled(false);
      }
    }
    if (steps[activeStep].name === "configureOptimizer") {
      const allModelsHaveOptimizers = newExp.runs.every((model) => {
        if (checkIfHaveOptimazers(model)) {
          return model.optimizer_name;
        }
        return true;
      });
      if (newExp.runs.length && allModelsHaveOptimizers) {
        setNextEnabled(true);
      } else {
        setNextEnabled(false);
      }
    }
  }, [open, newExp.runs]);

  return (
    <Dialog
      open={open}
      fullScreen={screenSm}
      fullWidth
      maxWidth={"lg"}
      onClose={() => {}} // No cerrar automáticamente
      disableEscapeKeyDown // Evitar cierre con Escape
      aria-labelledby="new-experiment-dialog-title"
      aria-describedby="new-experiment-dialog-description"
      scroll="paper"
      slotProps={{
        paper: {
          sx: { minHeight: "80vh" },
        },
      }}
    >
      {/* Title */}
      <DialogTitle id="new-experiment-dialog-title">
        <Grid container direction={"row"} alignItems={"center"}>
          <Grid size={{ xs: 12, md: 3 }}>
            <Grid
              container
              direction="row"
              alignItems="center"
              justifyContent="space-between"
            >
              <Grid size={{ xs: 1 }}>
                <IconButton
                  edge="start"
                  color="inherit"
                  onClick={handleCloseDialog}
                  sx={{ display: { xs: "flex", sm: "none" } }}
                >
                  <CloseIcon />
                </IconButton>
              </Grid>
              <Grid size={{ xs: 11 }}>
                <Typography
                  variant="h6"
                  component="h3"
                  align={matches ? "center" : "left"}
                  sx={{ mb: { sm: 2, md: 0 } }}
                >
                  {t("experiments:button.newExperiment")}
                </Typography>
              </Grid>
            </Grid>
          </Grid>
          <Grid size={{ xs: 12, md: 9 }}>
            <Stepper
              nonLinear
              activeStep={activeStep}
              sx={{ maxWidth: "100%" }}
            >
              {steps.map((step, index) => (
                <Step
                  key={`${step.name}`}
                  completed={activeStep > index}
                  disabled={activeStep < index}
                >
                  <StepButton color="inherit" onClick={handleStepButton(index)}>
                    {step.label}
                  </StepButton>
                </Step>
              ))}
            </Stepper>
          </Grid>
        </Grid>
        {/* Close button for larger screens */}
        <IconButton
          onClick={handleCloseDialog}
          sx={{
            position: "absolute",
            right: 8,
            top: 8,
            color: (theme) => theme.palette.grey[500],
            display: { xs: "none", sm: "flex" },
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      {/* Main content - steps */}
      <DialogContent dividers>
        {renderStep(
          steps[activeStep].name,
          newExp,
          setNewExp,
          setNextEnabled,
          defaultName,
          existingExperiments,
        )}
      </DialogContent>
      {/* Actions - Back and Next */}
      <DialogActions>
        <ButtonGroup size="large">
          <Button onClick={handleBackButton}>
            {activeStep === 0 ? t("common:close") : t("common:back")}
          </Button>
          <TimestampWrapper
            eventName={
              steps[activeStep].name === "prepareDataset"
                ? TIMESTAMP_KEYS.experiments.configureModel
                : steps[activeStep].name === "configureModels"
                  ? TIMESTAMP_KEYS.experiments.submitModel
                  : steps[activeStep].name === "configureOptimizer"
                    ? TIMESTAMP_KEYS.experiments.configureOptimazer
                    : null
            }
          >
            <Button
              data-tour={
                steps[activeStep].name === "selectTask"
                  ? "exp-task-selector-next-button"
                  : steps[activeStep].name === "selectDataset"
                    ? "exp-dataset-selector-next-button"
                    : steps[activeStep].name === "prepareDataset"
                      ? "exp-prepare-dataset-next-button"
                      : steps[activeStep].name === "configureModels"
                        ? "exp-configure-models-next-button"
                        : steps[activeStep].name === "configureOptimizer"
                          ? "exp-configure-optimizer-next-button"
                          : undefined
              }
              onClick={handleNextButton}
              autoFocus
              variant="contained"
              color="primary"
              disabled={!nextEnabled}
            >
              {activeStep === steps.length - 1
                ? t("common:save")
                : t("common:next")}
            </Button>
          </TimestampWrapper>
        </ButtonGroup>
      </DialogActions>
    </Dialog>
  );
}

NewExperimentModal.propTypes = {
  open: PropTypes.bool.isRequired,
  setOpen: PropTypes.func.isRequired,
  updateExperiments: PropTypes.func.isRequired,
  preselectedDataset: PropTypes.object,
  setPreselectedDataset: PropTypes.func.isRequired,
  existingExperiments: PropTypes.array,
};
