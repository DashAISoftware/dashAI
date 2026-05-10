import React, { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  ButtonGroup,
  Collapse,
  Paper,
  Step,
  StepButton,
  Stepper,
  Typography,
} from "@mui/material";
import { LoadingButton } from "@mui/lab";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import {
  createGlobalExplainer as createGlobalExplainerRequest,
  createLocalExplainer as createLocalExplainerRequest,
  getExplainers,
} from "../../api/explainer";
import { enqueueExplainerJob as enqueueExplainerJobRequest } from "../../api/job";
import { startJobPolling } from "../../utils/jobPoller";
import TimestampWrapper from "../shared/TimestampWrapper";
import { TIMESTAMP_KEYS } from "../../constants/timestamp";
import { generateSequentialName } from "../../utils/nameGenerator";
import ConfigureExplainerStep from "./ConfigureExplainerStep";
import SelectDatasetStep from "./SelectDatasetStep";
import SetNameAndExplainerStep from "./SetNameAndExplainerStep";

const SNACKBAR_AUTO_HIDE_MS = 5000;

const getNextExplainerName = (scope, existingExplainers = []) => {
  const { defaultName } = generateSequentialName({
    base: scope === "local" ? "Explainer_local" : "Explainer_global",
    items: existingExplainers,
    getName: (explainer) => explainer?.name,
  });

  return defaultName;
};

export default function InlineExplainerCreator({
  open,
  scope,
  explainerConfig,
  onCreated,
  onCancel,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["explainers", "common"]);
  const formSubmitRef = useRef(null);

  const { runId, taskName } = explainerConfig;
  const isLocal = scope === "local";

  const defaultNewExplainer = useMemo(
    () =>
      isLocal
        ? {
            name: "",
            run_id: runId,
            explainer_name: null,
            scope: { split: "test", percentage: 20 },
            dataset_id: null,
            parameters: null,
            fit_parameters: null,
          }
        : {
            name: "",
            run_id: runId,
            explainer_name: null,
            parameters: null,
          },
    [isLocal, runId],
  );

  const steps = useMemo(
    () =>
      isLocal
        ? [
            {
              name: "selectExplainer",
              label: t("explainers:label.selectExplainer"),
            },
            {
              name: "selectDataset",
              label: t("explainers:label.selectDataset"),
            },
            {
              name: "configureExplainer",
              label: t("explainers:label.configureExplainerParameters"),
            },
          ]
        : [
            {
              name: "selectExplainer",
              label: t("explainers:label.selectExplainer"),
            },
            {
              name: "configureExplainer",
              label: t("explainers:label.configureExplainerParameters"),
            },
          ],
    [isLocal, t],
  );

  const [activeStep, setActiveStep] = useState(0);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [newExpl, setNewExpl] = useState(defaultNewExplainer);
  const [existingExplainers, setExistingExplainers] = useState([]);
  const [existingExplainersLoaded, setExistingExplainersLoaded] =
    useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const resetState = () => {
    setActiveStep(0);
    setNewExpl(defaultNewExplainer);
    setNextEnabled(false);
    setExistingExplainers([]);
    setExistingExplainersLoaded(false);
  };

  const loadExistingExplainers = async () => {
    try {
      const explainers = await getExplainers(undefined, scope);
      setExistingExplainers(explainers);
    } catch (error) {
      console.error("Error loading existing explainers:", error);
      setExistingExplainers([]);
    } finally {
      setExistingExplainersLoaded(true);
    }
  };

  useEffect(() => {
    if (open) {
      setExistingExplainersLoaded(false);
      loadExistingExplainers();
      return;
    }

    resetState();
  }, [open]);

  useEffect(() => {
    if (!open || !existingExplainersLoaded || newExpl.name.trim()) {
      return;
    }

    setNewExpl((prev) => ({
      ...prev,
      name: getNextExplainerName(scope, existingExplainers),
    }));
  }, [open, existingExplainersLoaded, existingExplainers, newExpl.name, scope]);

  const enqueueExplainerJob = async (explainerId) => {
    try {
      const response = await enqueueExplainerJobRequest(explainerId, scope);
      enqueueSnackbar(
        t(
          isLocal
            ? "explainers:message.localExplainerJobCreated"
            : "explainers:message.globalExplainerJobCreated",
        ),
        {
          variant: "success",
          autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
        },
      );

      if (response && response.id) {
        startJobPolling(
          response.id,
          () => {
            enqueueSnackbar(
              t("explainers:message.explainerJobCompleted", {
                name: newExpl.name,
              }),
              {
                variant: "success",
                autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
              },
            );
            if (onCreated) {
              onCreated();
            }
          },
          (result) => {
            console.error(`${scope} explainer job failed:`, result);
            enqueueSnackbar(
              t(
                isLocal
                  ? "explainers:error.localExplainerJobFailed"
                  : "explainers:error.globalExplainerJobFailed",
                {
                  error: result.error || "Unknown error",
                },
              ),
              {
                variant: "error",
                autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
              },
            );
            if (onCreated) {
              onCreated();
            }
          },
        );
      }

      return response;
    } catch (error) {
      enqueueSnackbar(
        t(
          isLocal
            ? "explainers:error.localExplainerJobEnqueueError"
            : "explainers:error.globalExplainerJobEnqueueError",
        ),
        {
          variant: "error",
          autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
        },
      );
      console.error("Error details:", error);
      throw error;
    }
  };

  const uploadNewExplainer = async () => {
    try {
      setIsLoading(true);

      const response = isLocal
        ? await createLocalExplainerRequest(
            newExpl.name,
            newExpl.run_id,
            newExpl.explainer_name,
            newExpl.dataset_id,
            newExpl.parameters,
            newExpl.fit_parameters,
            newExpl.scope,
          )
        : await createGlobalExplainerRequest(
            newExpl.name,
            newExpl.run_id,
            newExpl.explainer_name,
            newExpl.parameters,
          );

      await enqueueExplainerJob(response.id);
      await loadExistingExplainers();
      if (onCreated) onCreated();
      return true;
    } catch (error) {
      enqueueSnackbar(
        t(
          isLocal
            ? "explainers:error.localExplainerCreationError"
            : "explainers:error.globalExplainerCreationError",
        ),
        {
          variant: "error",
          autoHideDuration: SNACKBAR_AUTO_HIDE_MS,
        },
      );
      console.error("Error details:", error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const handleStepButton = (stepIndex) => () => {
    setActiveStep(stepIndex);
  };

  const handleBackButton = () => {
    if (activeStep === 0) {
      onCancel();
      return;
    }

    setActiveStep((prev) => prev - 1);
    setNextEnabled(true);
  };

  const handleNextButton = async () => {
    if (activeStep < steps.length - 1) {
      setActiveStep((prev) => prev + 1);
      setNextEnabled(false);
      return;
    }

    const isSuccess = await uploadNewExplainer();
    if (isSuccess) {
      resetState();
      onCancel();
    }
  };

  return (
    <Collapse in={open} timeout="auto" unmountOnExit>
      <Paper variant="outlined" sx={{ p: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 2 }}>
            {t(
              isLocal
                ? "explainers:label.newLocalExplainer"
                : "explainers:label.newGlobalExplainer",
            )}
          </Typography>
          <Stepper nonLinear activeStep={activeStep} sx={{ maxWidth: "100%" }}>
            {steps.map((step, index) => (
              <Step
                key={step.name}
                completed={false}
                disabled={activeStep < index}
              >
                <StepButton color="inherit" onClick={handleStepButton(index)}>
                  {step.label}
                </StepButton>
              </Step>
            ))}
          </Stepper>
        </Box>

        <Box sx={{ mb: 4 }}>
          {activeStep === 0 && (
            <SetNameAndExplainerStep
              newExpl={newExpl}
              setNewExpl={setNewExpl}
              setNextEnabled={setNextEnabled}
              scope={isLocal ? "Local" : "Global"}
              taskName={taskName}
              existingExplainers={existingExplainers}
            />
          )}
          {isLocal && activeStep === 1 && (
            <SelectDatasetStep
              newExpl={newExpl}
              setNewExpl={setNewExpl}
              setNextEnabled={setNextEnabled}
            />
          )}
          {((isLocal && activeStep === 2) ||
            (!isLocal && activeStep === 1)) && (
            <ConfigureExplainerStep
              newExpl={newExpl}
              setNewExpl={setNewExpl}
              setNextEnabled={setNextEnabled}
              formSubmitRef={formSubmitRef}
              scope={isLocal ? "Local" : "global"}
            />
          )}
        </Box>

        <ButtonGroup size="large">
          <Button onClick={handleBackButton} disabled={isLoading}>
            {activeStep === 0 ? t("common:cancel") : t("common:back")}
          </Button>
          <TimestampWrapper
            eventName={
              activeStep === steps.length - 1
                ? isLocal
                  ? TIMESTAMP_KEYS.explainer.submitLocal
                  : TIMESTAMP_KEYS.explainer.submitGlobal
                : null
            }
          >
            <LoadingButton
              onClick={handleNextButton}
              variant="contained"
              color="primary"
              disabled={!nextEnabled || isLoading}
              loading={isLoading}
            >
              {activeStep === steps.length - 1
                ? t("common:save")
                : t("common:next")}
            </LoadingButton>
          </TimestampWrapper>
        </ButtonGroup>
      </Paper>
    </Collapse>
  );
}

InlineExplainerCreator.propTypes = {
  open: PropTypes.bool.isRequired,
  scope: PropTypes.oneOf(["global", "local"]).isRequired,
  explainerConfig: PropTypes.shape({
    runId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    taskName: PropTypes.string,
  }).isRequired,
  onCreated: PropTypes.func,
  onCancel: PropTypes.func.isRequired,
};
