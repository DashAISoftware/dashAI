import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, Button, CircularProgress } from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  Close as CloseIcon,
} from "@mui/icons-material";
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
}) {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [modelSession, setModelSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["prediction", "common"]);

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

      if (onSaved) onSaved(prediction);
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
        (result) => {
          console.error("Prediction job failed:", result);
          enqueueSnackbar(
            t("prediction:error.predictionFailed", {
              error: result.error || t("common:unknownError"),
            }),
            { variant: "error" },
          );
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

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
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

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button
          variant="contained"
          size="small"
          startIcon={
            isSubmitting ? (
              <CircularProgress size={14} color="inherit" />
            ) : (
              <TrendingUpIcon />
            )
          }
          onClick={handleRunDatasetPrediction}
          disabled={!selectedDataset || isSubmitting}
        >
          {t("prediction:button.runPrediction")}
        </Button>

        <Button
          variant="text"
          size="small"
          startIcon={<CloseIcon />}
          onClick={onClose}
          disabled={isSubmitting}
          color="inherit"
        >
          {t("common:cancel")}
        </Button>
      </Box>
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
