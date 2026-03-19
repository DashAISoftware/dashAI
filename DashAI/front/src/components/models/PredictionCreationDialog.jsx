import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  CircularProgress,
  IconButton,
  Stepper,
  Step,
  StepLabel,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import DatasetSelector from "../predictions/DatasetSelector";
import ManualInput from "../predictions/ManualInput";
import { createPrediction, filterDatasets } from "../../api/predict";
import {
  getDatasetInfo,
  getDatasetTypes,
  getDatasetSample,
} from "../../api/datasets";
import { enqueuePredictionJob } from "../../api/job";
import { getModelSessionById } from "../../api/modelSession";
import { useSnackbar } from "notistack";
import { startJobPolling } from "../../utils/jobPoller";
import { getPredictions } from "../../api/predict";

import { useTranslation } from "react-i18next";

/**
 * PredictionCreationDialog - Wizard for creating new predictions
 */
export default function PredictionCreationDialog({
  open,
  onClose,
  run,
  session,
  onPredictionCreated,
  defaultMode = "dataset",
}) {
  const [activeStep, setActiveStep] = useState(0);
  const [predictionMode, setPredictionMode] = useState(defaultMode); // Initial value only — not synced with prop
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [manualRows, setManualRows] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const [modelSession, setModelSession] = useState(null);
  const [types, setTypes] = useState({});
  const [sample, setSample] = useState(null);
  const [loadingExperiment, setLoadingExperiment] = useState(true);

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["prediction", "common"]);

  const steps = [
    t("prediction:label.configureInput"),
    t("prediction:label.confirm"),
  ];

  useEffect(() => {
    if (!open) {
      setActiveStep(0);
      setPredictionMode(defaultMode);
      setDatasets([]);
      setSelectedDataset(null);
      setManualRows([]);
      setIsLoading(false);
    }
  }, [open, defaultMode]);

  useEffect(() => {
    const fetchData = async () => {
      if (!run || !open) return;

      setLoadingExperiment(true);

      try {
        const availableDatasets = await filterDatasets({ run_id: run.id });
        const availableDatasetsWithInfo = await Promise.all(
          availableDatasets.map(async (dataset) => {
            const datasetInfo = await getDatasetInfo(dataset.id);
            return { ...dataset, ...datasetInfo };
          }),
        );
        setDatasets(availableDatasetsWithInfo);

        if (run.model_session_id || session?.id) {
          const sessionData = await getModelSessionById(
            run.model_session_id || session.id,
          );
          setModelSession(sessionData);

          const datasetTypes = await getDatasetTypes(sessionData.dataset_id);
          setTypes(datasetTypes);

          const datasetSample = await getDatasetSample(sessionData.dataset_id);
          setSample(datasetSample);
        }
      } catch (error) {
        console.error("Error fetching data:", error);
        enqueueSnackbar(t("prediction:error.loadingPredictionData"), {
          variant: "error",
        });
      } finally {
        setLoadingExperiment(false);
      }
    };

    fetchData();
  }, [run, session, open, enqueueSnackbar]);

  const canProceed = () => {
    if (activeStep === 0) return true;
    if (activeStep === 1) {
      if (predictionMode === "dataset") {
        return selectedDataset !== null;
      }
      return manualRows && manualRows.length > 0;
    }
    return true;
  };

  const handleNext = () => {
    if (activeStep < steps.length - 1) {
      setActiveStep((prev) => prev + 1);
    } else {
      handleSubmit();
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleSubmit = async () => {
    setIsLoading(true);

    try {
      const prediction = await createPrediction(
        run.id,
        predictionMode === "dataset" ? selectedDataset.id : null,
      );

      const jobResponse = await enqueuePredictionJob(
        prediction.id,
        predictionMode === "manual" ? manualRows : null,
      );

      if (!jobResponse || !jobResponse.id) {
        throw new Error("Failed to enqueue prediction job");
      }

      enqueueSnackbar(t("prediction:message.predictionJobSubmitted"), {
        variant: "success",
      });

      startJobPolling(
        jobResponse.id,
        async () => {
          const updatedPredictions = await getPredictions(run.id);
          const updatedPrediction = updatedPredictions.find(
            (p) => p.id === prediction.id,
          );

          enqueueSnackbar(t("prediction:message.predictionCompleted"), {
            variant: "success",
          });

          if (onPredictionCreated) {
            onPredictionCreated(updatedPrediction || prediction);
          }
        },
        (result) => {
          // On failure
          console.error("Prediction job failed:", result);
          enqueueSnackbar(
            t("prediction:error.predictionFailed", {
              error: result.error || t("common:unknownError"),
            }),
            { variant: "error" },
          );

          if (onPredictionCreated) {
            onPredictionCreated();
          }
        },
      );

      if (onPredictionCreated) {
        onPredictionCreated(prediction);
      }

      onClose();
    } catch (error) {
      console.error("Error creating prediction:", error);
      enqueueSnackbar(t("prediction:error.creatingPrediction"), {
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Box sx={{ py: 2 }}>
            {predictionMode === "dataset" ? (
              <>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 2 }}
                >
                  {t("prediction:label.selectDataset")}
                </Typography>
                <DatasetSelector
                  experiment={modelSession}
                  datasets={datasets}
                  selectedDataset={selectedDataset}
                  setSelectedDataset={setSelectedDataset}
                />
              </>
            ) : (
              <>
                <ManualInput
                  experiment={modelSession}
                  loading={loadingExperiment}
                  types={types}
                  sample={sample}
                  manualInputData={manualRows}
                  setManualInputData={setManualRows}
                />
              </>
            )}
          </Box>
        );

      case 1:
        return (
          <Box sx={{ py: 2 }}>
            <Typography variant="h6" gutterBottom>
              {t("prediction:label.confirmPrediction")}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t("prediction:label.reviewDetails")}
            </Typography>
            <Box sx={{ bgcolor: "background.default", p: 2, borderRadius: 1 }}>
              <Typography variant="body2">
                <strong>{t("common:model")}:</strong> {run.model_name}
              </Typography>
              <Typography variant="body2">
                <strong>{t("common:run")}:</strong> {run.name}
              </Typography>
              <Typography variant="body2">
                <strong>{t("prediction:label.inputType")}:</strong>{" "}
                {predictionMode === "dataset"
                  ? t("common:dataset")
                  : t("prediction:label.manualInput")}
              </Typography>
              {predictionMode === "dataset" && selectedDataset && (
                <Typography variant="body2">
                  <strong>{t("common:dataset")}:</strong> {selectedDataset.name}
                </Typography>
              )}
              {predictionMode === "manual" && (
                <Typography variant="body2">
                  <strong>{t("prediction:label.manualRows")}:</strong>{" "}
                  {manualRows.length}
                </Typography>
              )}
            </Box>
          </Box>
        );

      default:
        return null;
    }
  };

  if (!run) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6">
            {t("prediction:label.createNewPrediction")}
          </Typography>
          <IconButton onClick={onClose} size="small">
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

        {loadingExperiment && activeStep === 0 ? (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: 200,
            }}
          >
            <CircularProgress />
          </Box>
        ) : (
          renderStepContent(activeStep)
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} disabled={isLoading}>
          {t("common:cancel")}
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button onClick={handleBack} disabled={activeStep === 0 || isLoading}>
          {t("common:back")}
        </Button>
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={!canProceed() || isLoading || loadingExperiment}
          startIcon={isLoading && <CircularProgress size={16} />}
        >
          {activeStep === steps.length - 1
            ? isLoading
              ? t("common:submitting")
              : t("common:submit")
            : t("common:next")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

PredictionCreationDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string,
    model_name: PropTypes.string,
    model_session_id: PropTypes.number,
  }).isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
  }),
  onPredictionCreated: PropTypes.func,
  defaultMode: PropTypes.oneOf(["dataset", "manual"]),
};
