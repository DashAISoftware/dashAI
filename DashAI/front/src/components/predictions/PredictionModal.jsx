import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Tabs,
  Tab,
  IconButton,
  Typography,
  Chip,
  CircularProgress,
  Divider,
} from "@mui/material";
import {
  Close as CloseIcon,
  Download as DownloadIcon,
  CheckCircle as CheckCircleIcon,
  PlayArrow as PlayIcon,
} from "@mui/icons-material";
import ModeSelector from "./ModeSelector";
import DatasetSelector from "./DatasetSelector";
import ForecastingOptions from "./ForecastingOptions";
import ResultsTable from "./ResultsTable";
import PredictionsTable from "./PredictionsTable";
import ManualInput from "./ManualInput";
import {
  createPrediction,
  filterDatasets,
  getPredictions,
  deletePrediction,
} from "../../api/predict";
import {
  getDatasetInfo,
  exportDatasetCsvByPath,
  getDatasetTemporalInfo,
  getDatasetTypes,
  getDatasetSample,
} from "../../api/datasets";
import { enqueuePredictionJob } from "../../api/job";
import { getModelSessionById } from "../../api/modelSession";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { getPredictionStatus } from "../../utils/predictionStatus";

export default function PredictionModal({ isOpen, onClose, run }) {
  const [activeTab, setActiveTab] = useState(0);
  const [predictionMode, setPredictionMode] = useState("dataset");
  const [viewMode, setViewMode] = useState("input");
  const [datasets, setDatasets] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const [selectedDataset, setSelectedDataset] = useState(null);
  const [manualRows, setManualRows] = useState([]);

  const [predictions, setPredictions] = useState([]);
  const [selectedPrediction, setSelectedPrediction] = useState(null);

  // Experiment-related states
  const [experiment, setExperiment] = useState(null);
  const [types, setTypes] = useState({});
  const [loadingExperiment, setLoadingExperiment] = useState(true);
  const [sample, setSample] = useState(null);

  // ── Forecasting-specific state ──
  const [temporalInfo, setTemporalInfo] = useState(null);
  const [forecastMode, setForecastMode] = useState("dataset"); // "auto-generate" | "dataset"
  const [forecastPeriods, setForecastPeriods] = useState(null);

  const isForecastingTask = experiment?.task_name === "ForecastingTask";

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["prediction", "common"]);

  // Reset state when modal is closed
  useEffect(() => {
    if (!isOpen) {
      setActiveTab(0);
      setPredictionMode("dataset");
      setViewMode("input");
      setDatasets([]);
      setSelectedDataset(null);
      setPredictions([]);
      setIsLoading(false);
      setManualRows([]);
      setSelectedPrediction(null);
      // Reset forecasting state
      setTemporalInfo(null);
      setForecastMode("dataset");
      setForecastPeriods(null);
    }
  }, [isOpen]);

  useEffect(() => {
    // Fetch available datasets for prediction
    const fetchDatasets = async () => {
      if (run) {
        try {
          const availableDatasets = await filterDatasets({ run_id: run.id });
          const availableDatasetsWithInfo = await Promise.all(
            availableDatasets.map(async (dataset) => {
              // Fetch additional info about the datasets
              const datasetInfo = await getDatasetInfo(dataset.id);
              return { ...dataset, ...datasetInfo };
            }),
          );

          setDatasets(availableDatasetsWithInfo);
        } catch (error) {
          console.error("Error fetching datasets:", error);
          enqueueSnackbar(t("prediction:error.fetchingDatasets"), {
            variant: "error",
          });
        }
      }
    };

    // Fetch previous predictions for this run
    const fetchPredictions = async () => {
      if (run) {
        try {
          const preds = await getPredictions(run.id);
          setPredictions(preds);
        } catch (error) {
          console.error("Error fetching predictions:", error);
          enqueueSnackbar(t("prediction:error.loadingPreviousPredictions"), {
            variant: "error",
          });
        }
      }
    };

    // Fetch experiment details + forecasting temporal info
    const fetchExperiment = async () => {
      setLoadingExperiment(true);
      try {
        if (run && run.model_session_id) {
          const experimentData = await getModelSessionById(
            run.model_session_id,
          );
          setExperiment(experimentData);

          const datasetTypes = await getDatasetTypes(experimentData.dataset_id);
          setTypes(datasetTypes);
          const datasetSample = await getDatasetSample(
            experimentData.dataset_id,
          );
          setSample(datasetSample);

          // ── Forecasting: fetch temporal info if applicable ──
          if (experimentData.task_name === "ForecastingTask") {
            try {
              const inputCols = experimentData.input_columns || [];
              // In forecasting, the first input column is the timestamp column
              if (inputCols.length > 0 && experimentData.dataset_id) {
                const timestampColumn =
                  typeof inputCols === "string"
                    ? JSON.parse(inputCols)[0]
                    : inputCols[0];
                const info = await getDatasetTemporalInfo(
                  experimentData.dataset_id,
                  timestampColumn,
                );
                setTemporalInfo(info);
              }
            } catch (error) {
              console.error("Error fetching temporal info:", error);
            }
          }
        }
      } catch (error) {
        console.error("Error fetching experiment:", error);
      } finally {
        setLoadingExperiment(false);
      }
    };

    fetchPredictions();
    fetchExperiment();
    fetchDatasets();
  }, [run]);

  // Handle prediction execution
  const submitPredictionJob = async () => {
    setIsLoading(true);

    try {
      // Determine dataset_id — null when auto-generating timestamps
      const datasetId =
        isForecastingTask && forecastMode === "auto-generate"
          ? null
          : predictionMode === "dataset"
            ? (selectedDataset?.id ?? null)
            : null;

      // 1. Create prediction record
      const prediction = await createPrediction(run.id, datasetId);

      // 2. Enqueue prediction job (with forecast_periods when applicable)
      const periodsArg =
        isForecastingTask && forecastMode === "auto-generate"
          ? forecastPeriods
          : undefined;

      await enqueuePredictionJob(
        prediction.id,
        predictionMode === "manual" ? manualRows : null,
        periodsArg,
      );
      enqueueSnackbar(t("prediction:message.predictionJobSubmitted"), {
        variant: "success",
      });

      // 3. Update status and navigate
      prediction.status = 1; // Delivered
      setPredictions([prediction, ...predictions]);
      setSelectedPrediction(prediction);
      setActiveTab(1);
    } catch (error) {
      console.error("Error submitting prediction job:", error);
      enqueueSnackbar(t("prediction:error.submittingPredictionJob"), {
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Polling for running prediction results
  useEffect(() => {
    if (!predictions || predictions.length === 0) return;

    // Predictions that are still running
    const pending = predictions.filter(
      (p) =>
        p.status === 1 || // Delivered
        p.status === 2, // Started
    );

    if (pending.length === 0) return;

    const intervals = {};

    pending.forEach((prediction) => {
      intervals[prediction.id] = setInterval(async () => {
        try {
          const updated = (await getPredictions(null, prediction.id))[0];

          // Update predictions list
          setPredictions((prev) =>
            prev.map((p) => (p.id === updated.id ? updated : p)),
          );

          // Update selected prediction if it's the one being polled
          setSelectedPrediction((prev) => {
            if (prev && prev.id === updated.id) {
              return updated;
            }
            return prev;
          });

          const statusText = updated.status;

          // If prediction is completed or failed, stop polling
          if (statusText === 3 || statusText === 4) {
            // Finished or Error
            enqueueSnackbar(
              `${t("prediction:label.prediction")} ${
                updated.id
              } ${getPredictionStatus(statusText, t).toLowerCase()}.`,
              {
                variant: statusText === 3 ? "success" : "error",
              },
            );
            clearInterval(intervals[prediction.id]);
            delete intervals[prediction.id];
          }
        } catch (error) {
          console.error("Error polling prediction:", error);
          enqueueSnackbar(t("prediction:error.updatingPredictionStatus"), {
            variant: "error",
          });
        }
      }, 2000);
    });

    return () => {
      Object.values(intervals).forEach((interval) => clearInterval(interval));
    };
  }, [predictions]);

  const handleDownload = async (selectedPrediction) => {
    const data = await exportDatasetCsvByPath(selectedPrediction.results_path);
    const blob = new Blob([data], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute(
      "download",
      `${"prediction-" + selectedPrediction.created}.csv`,
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDeletePrediction = async (predictionId) => {
    try {
      await deletePrediction(predictionId);
      setPredictions((prev) =>
        prev.filter((prediction) => prediction.id !== predictionId),
      );
      if (selectedPrediction && selectedPrediction.id === predictionId) {
        setSelectedPrediction(null);
      }
      enqueueSnackbar(t("prediction:message.deletedSuccessfully"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Error deleting prediction:", error);
      enqueueSnackbar(t("prediction:error.errorDeleting"), {
        variant: "error",
      });
    }
  };

  const canPredict = () => {
    // ── Forecasting-specific logic ──
    if (isForecastingTask) {
      if (forecastMode === "auto-generate") {
        return forecastPeriods != null && forecastPeriods > 0;
      }
      // forecastMode === "dataset": need a dataset selected
      return selectedDataset !== null;
    }

    // ── Standard tasks ──
    if (predictionMode === "dataset") {
      return selectedDataset !== null;
    }
    return manualRows && manualRows.length > 0;
  };

  if (!isOpen || !run) return null;

  return (
    <Dialog open={isOpen} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Box>
            <Typography variant="h6">
              {t("prediction:label.modelPrediction")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {run.model_name.display_name ?? run.model_name.name}
            </Typography>
          </Box>
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <Divider />

      <Box
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          px: 3,
        }}
      >
        <Tabs
          centered
          sx={{
            minHeight: "55px",
            "& .MuiTab-root": {
              minHeight: "55px",
              fontSize: "0.85rem",
            },
            "& .MuiTabs-indicator": {
              height: "2px",
            },
          }}
          value={activeTab}
          onChange={(e, newValue) => {
            setActiveTab(newValue);
            setSelectedPrediction(null);
          }}
          onClick={() => setSelectedPrediction(null)}
        >
          <Tab label={t("prediction:label.newPrediction")} />
          <Tab label={t("prediction:label.previousPredictions")} />
        </Tabs>
      </Box>

      <Divider />

      <DialogContent sx={{ height: 800, minHeight: "unset", overflow: "auto" }}>
        {activeTab === 0 && (
          <>
            {viewMode === "input" ? (
              <Box>
                {/* ── Forecasting: show ForecastingOptions instead of ModeSelector ── */}
                {isForecastingTask ? (
                  <>
                    <ForecastingOptions
                      temporalInfo={temporalInfo}
                      forecastMode={forecastMode}
                      setForecastMode={setForecastMode}
                      forecastPeriods={forecastPeriods}
                      setForecastPeriods={setForecastPeriods}
                      selectedDataset={selectedDataset}
                    />
                    {/* Show DatasetSelector only when forecasting uses dataset mode */}
                    {forecastMode === "dataset" && (
                      <DatasetSelector
                        experiment={experiment}
                        datasets={datasets}
                        selectedDataset={selectedDataset}
                        setSelectedDataset={setSelectedDataset}
                      />
                    )}
                  </>
                ) : (
                  <>
                    {/* ── Standard tasks: original mode selector ── */}
                    <ModeSelector
                      predictionMode={predictionMode}
                      setPredictionMode={setPredictionMode}
                    />
                    {predictionMode === "dataset" ? (
                      <DatasetSelector
                        experiment={experiment}
                        datasets={datasets}
                        selectedDataset={selectedDataset}
                        setSelectedDataset={setSelectedDataset}
                      />
                    ) : (
                      <ManualInput
                        experiment={experiment}
                        loading={loadingExperiment}
                        types={types}
                        sample={sample}
                        manualInputData={manualRows}
                        setManualInputData={setManualRows}
                      />
                    )}
                  </>
                )}
              </Box>
            ) : (
              <ResultsTable selectedPrediction={selectedPrediction} />
            )}
          </>
        )}

        {activeTab === 1 && (
          <>
            {selectedPrediction ? (
              <Box>
                <ResultsTable selectedPrediction={selectedPrediction} />
              </Box>
            ) : (
              <PredictionsTable
                predictions={predictions}
                onItemClick={(item) => {
                  setSelectedPrediction(item);
                }}
                onItemDelete={handleDeletePrediction}
              />
            )}
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        {activeTab === 0 ? (
          <>
            <Button variant="outlined" onClick={onClose}>
              {t("common:close")}
            </Button>
            <Button
              variant="contained"
              onClick={submitPredictionJob}
              disabled={!canPredict() || isLoading}
              startIcon={isLoading && <CircularProgress size={16} />}
            >
              {isLoading
                ? t("prediction:label.predicting")
                : t("prediction:button.runPrediction")}
            </Button>
          </>
        ) : selectedPrediction ? (
          <>
            <Button
              variant="outlined"
              onClick={() => setSelectedPrediction(null)}
            >
              {t("common:back")}
            </Button>
            <Button
              variant="contained"
              disabled={
                selectedPrediction?.status !== 3 // Finished
              }
              startIcon={<DownloadIcon />}
              onClick={() => handleDownload(selectedPrediction)}
            >
              {t("common:downloadCSV")}
            </Button>
          </>
        ) : (
          <Button variant="outlined" onClick={onClose}>
            {t("common:close")}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
