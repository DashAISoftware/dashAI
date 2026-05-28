import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Box, CircularProgress } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import DatasetSelector from "../predictions/DatasetSelector";
import {
  createPrediction,
  filterDatasets,
  getPredictions,
} from "../../api/predict";
import { enqueuePredictionJob } from "../../api/job";
import { getDatasetInfo } from "../../api/datasets";
import { getModelSessionById } from "../../api/modelSession";
import { startJobPolling } from "../../utils/jobPoller";

/**
 * DatasetPredictionPanel
 */
export default function DatasetPredictionPanel({
  run,
  session,
  onSaved,
  onClose,
  runRef = null,
  onStateChange = null,
}) {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [modelSession, setModelSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["prediction", "common"]);

  const handleRunRef = useRef(null);
  useEffect(() => {
    if (runRef) runRef.current = () => handleRunRef.current?.();
  }, [runRef]);

  useEffect(() => {
    onStateChange?.({
      canRun: !!selectedDataset && !isSubmitting,
      isSubmitting,
    });
  }, [selectedDataset, isSubmitting, onStateChange]);

  useEffect(() => {
    const fetchData = async () => {
      if (!run?.id) return;
      setLoading(true);
      try {
        const [availableDatasets, sessionData] = await Promise.all([
          filterDatasets({ run_id: run.id }),
          getModelSessionById(run.model_session_id || session?.id),
        ]);

        const availableDatasetsWithInfo = await Promise.all(
          availableDatasets.map(async (dataset) => {
            const datasetInfo = await getDatasetInfo(dataset.id);
            return { ...dataset, ...datasetInfo };
          }),
        );

        setDatasets(availableDatasetsWithInfo);
        setModelSession(sessionData);
      } catch (error) {
        console.error("Error loading dataset prediction data:", error);
        enqueueSnackbar(t("prediction:error.loadingPredictionData"), {
          variant: "error",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [run, session, enqueueSnackbar, t]);

  const handleRunDatasetPrediction = async () => {
    if (!selectedDataset) return;

    setIsSubmitting(true);
    try {
      const prediction = await createPrediction(run.id, selectedDataset.id);
      const jobResponse = await enqueuePredictionJob(prediction.id);

      if (!jobResponse || !jobResponse.id) {
        throw new Error("Failed to enqueue prediction job");
      }

      enqueueSnackbar(t("prediction:message.predictionJobSubmitted"), {
        variant: "success",
      });

      let optimisticPrediction = prediction;
      try {
        const predictionsAfterEnqueue = await getPredictions(run.id);
        const freshlyCreated = predictionsAfterEnqueue.find(
          (p) => p.id === prediction.id,
        );
        optimisticPrediction = freshlyCreated || prediction;
      } catch (refreshError) {
        console.error(
          "Error refreshing prediction after enqueueing job:",
          refreshError,
        );
      }

      optimisticPrediction = {
        ...optimisticPrediction,
        dataset: optimisticPrediction.dataset || selectedDataset,
        status: optimisticPrediction.status ?? 1,
      };

      if (onSaved) onSaved(optimisticPrediction);
      onClose();

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
          if (onSaved) onSaved(updatedPrediction || prediction);
        },
        async (result) => {
          console.error("Prediction job failed:", result);
          enqueueSnackbar(
            t("prediction:error.predictionFailed", {
              error: result.error || t("common:unknownError"),
            }),
            { variant: "error" },
          );

          try {
            const updatedPredictions = await getPredictions(run.id);
            const updatedPrediction = updatedPredictions.find(
              (p) => p.id === prediction.id,
            );
            if (onSaved) onSaved(updatedPrediction || prediction);
          } catch (refreshError) {
            console.error(
              "Error refreshing prediction after job failure:",
              refreshError,
            );
          }
        },
      );
    } catch (error) {
      console.error("Error creating dataset prediction:", error);
      enqueueSnackbar(t("prediction:error.creatingPrediction"), {
        variant: "error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  handleRunRef.current = handleRunDatasetPrediction;

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }

  if (!modelSession) {
    return null;
  }

  return (
    <Box>
      <DatasetSelector
        experiment={modelSession}
        datasets={datasets}
        selectedDataset={selectedDataset}
        setSelectedDataset={setSelectedDataset}
      />
    </Box>
  );
}

DatasetPredictionPanel.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    model_session_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  }).isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
  }),
  onSaved: PropTypes.func,
  onClose: PropTypes.func.isRequired,
};
