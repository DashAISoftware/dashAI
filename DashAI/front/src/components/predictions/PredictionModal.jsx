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
import ResultsTable from "./ResultsTable";
import PredictionsTable from "./PredictionsTable";
import ManualInput from "./ManualInput";
import {
  createPrediction,
  filterDatasets,
  getPredictions,
  deletePrediction,
} from "../../api/predict";
import { getDatasetInfo, exportDatasetCsvByPath } from "../../api/datasets";
import { enqueuePredictionJob } from "../../api/job";
import { getModelSessionById } from "../../api/modelSession";
import { getDatasetTypes, getDatasetSample } from "../../api/datasets";
import { useSnackbar } from "notistack";
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

  const { enqueueSnackbar } = useSnackbar();

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
          enqueueSnackbar("Error fetching datasets for prediction.", {
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
          enqueueSnackbar("Error fetching previous predictions.", {
            variant: "error",
          });
        }
      }
    };

    // Fetch experiment details
    const fetchExperiment = async () => {
      setLoadingExperiment(true);
      try {
        if (run && run.experiment_id) {
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
    // 1.- Set loading to true
    setIsLoading(true);

    try {
      // 2.- Create a prediction in database
      const prediction = await createPrediction(
        run.id,
        predictionMode === "dataset" ? selectedDataset.id : null,
      );

      // 3.- Enqueue prediction job
      await enqueuePredictionJob(
        prediction.id,
        predictionMode === "manual" ? manualRows : null,
      );
      enqueueSnackbar("Prediction job submitted successfully.", {
        variant: "success",
      });

      // 4.- Change prediction status to Delivered
      prediction.status = 1; // Delivered

      // 5.- Add prediction to the list
      setPredictions([prediction, ...predictions]);

      // 6.- Set selected prediction to the new one and switch tab
      setSelectedPrediction(prediction);
      setActiveTab(1);
    } catch (error) {
      console.error("Error submitting prediction job:", error);
      enqueueSnackbar("Error submitting prediction job.", {
        variant: "error",
      });
    } finally {
      // 7.- Set loading to false
      setIsLoading(false);
    }
  };

  // Polling for running prediction results
  useEffect(() => {
    if (!predictions || predictions.length === 0) return;

    // Predictions that are still running
    const pending = predictions.filter(
      (p) =>
        getPredictionStatus(p.status) === "Delivered" ||
        getPredictionStatus(p.status) === "Started",
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

          const statusText = getPredictionStatus(updated.status);

          // If prediction is completed or failed, stop polling
          if (statusText === "Finished" || statusText === "Error") {
            enqueueSnackbar(
              `Prediction ${updated.id} ${statusText.toLowerCase()}.`,
              {
                variant: statusText === "Finished" ? "success" : "error",
              },
            );
            clearInterval(intervals[prediction.id]);
            delete intervals[prediction.id];
          }
        } catch (error) {
          console.error("Error polling prediction:", error);
          enqueueSnackbar("Error updating prediction status.", {
            variant: "error",
          });
        }
      }, 2000); // Every 2 seconds
    });

    // Cleanup
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
      enqueueSnackbar("Prediction deleted successfully.", {
        variant: "success",
      });
    } catch (error) {
      console.error("Error deleting prediction:", error);
      enqueueSnackbar("Error deleting prediction.", {
        variant: "error",
      });
    }
  };

  const canPredict = () => {
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
            <Typography variant="h6">Model Prediction</Typography>
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
          <Tab label="New Prediction" />
          <Tab label="Previous Predictions" />
        </Tabs>
      </Box>

      <Divider />

      <DialogContent sx={{ height: 800, minHeight: "unset", overflow: "auto" }}>
        {activeTab === 0 && (
          <>
            {viewMode === "input" ? (
              <Box>
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
              Close
            </Button>
            <Button
              variant="contained"
              onClick={submitPredictionJob}
              disabled={!canPredict() || isLoading}
              startIcon={isLoading && <CircularProgress size={16} />}
            >
              {isLoading ? "Predicting..." : "Run Prediction"}
            </Button>
          </>
        ) : selectedPrediction ? (
          <>
            <Button
              variant="outlined"
              onClick={() => setSelectedPrediction(null)}
            >
              Back
            </Button>
            <Button
              variant="contained"
              disabled={
                getPredictionStatus(selectedPrediction?.status) !== "Finished"
              }
              startIcon={<DownloadIcon />}
              onClick={() => handleDownload(selectedPrediction)}
            >
              Download CSV
            </Button>
          </>
        ) : (
          <Button variant="outlined" onClick={onClose}>
            Close
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
