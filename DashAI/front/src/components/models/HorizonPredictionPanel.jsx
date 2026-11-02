import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Alert, Box, TextField } from "@mui/material";
import { LoadingButton } from "@mui/lab";
import { PlayArrow as PlayArrowIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import {
  createPrediction,
  getPredictionSplits,
  getPredictions,
} from "../../api/predict";
import { enqueuePredictionJob } from "../../api/job";
import { startJobPolling } from "../../utils/jobPoller";
import { getApiErrorMessage } from "../../utils/apiError";

/**
 * Ask a run whose task predicts by horizon (`prediction_mode: "horizon"`) for
 * a forecast of a number of steps past the end of its series.
 *
 * The field starts on the horizon the run's backtest measured, which the
 * prediction options publish (GET /predict/splits/{run}). Asking for more is
 * allowed; the answer says how many steps no backtest measured and how many
 * it did, and the panel shows that while the field holds the horizon asked.
 */
export default function HorizonPredictionPanel({ run, onSaved }) {
  const { t } = useTranslation(["prediction", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const [horizon, setHorizon] = useState("");
  // The warning of the last prediction asked for, with the horizon it was
  // asked for: { horizon, unevaluated, evaluated }.
  const [warning, setWarning] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPredictionSplits(run.id)
      .then(({ horizon: measured }) => {
        if (cancelled) return;
        if (measured) setHorizon((current) => current || String(measured));
      })
      .catch((error) =>
        console.error("Error fetching the prediction options:", error),
      );
    return () => {
      cancelled = true;
    };
  }, [run.id]);

  const steps = Number(horizon);
  const isValid = Number.isInteger(steps) && steps >= 1;

  const handleRun = async () => {
    setIsSubmitting(true);
    try {
      const prediction = await createPrediction(run.id, null, null, steps);
      setWarning({
        horizon: steps,
        unevaluated: prediction.unevaluated_steps ?? 0,
        evaluated: prediction.evaluated_horizon ?? null,
      });
      const jobResponse = await enqueuePredictionJob(prediction.id);
      if (!jobResponse?.id) {
        throw new Error("Failed to enqueue prediction job");
      }
      enqueueSnackbar(t("prediction:message.predictionJobSubmitted"), {
        variant: "success",
      });
      onSaved(prediction);

      // Watching the job is what keeps the job queue polling, so the queue
      // lists it, and what tells the run's predictions it finished.
      const refreshPrediction = async () => {
        try {
          const predictions = await getPredictions(run.id);
          onSaved(
            predictions.find((p) => p.id === prediction.id) ?? prediction,
          );
        } catch (refreshError) {
          console.error("Error refreshing the prediction:", refreshError);
        }
      };
      startJobPolling(
        jobResponse.id,
        async () => {
          enqueueSnackbar(t("prediction:message.predictionCompleted"), {
            variant: "success",
          });
          await refreshPrediction();
        },
        async (result) => {
          const wasCancelled = result?.status === "cancelled";
          enqueueSnackbar(
            wasCancelled
              ? t("common:jobQueue.jobCancelled")
              : t("prediction:error.predictionFailed", {
                  error: result?.error || t("common:unknownError"),
                }),
            { variant: wasCancelled ? "info" : "error" },
          );
          await refreshPrediction();
        },
      );
    } catch (error) {
      enqueueSnackbar(getApiErrorMessage(error, t("common:unknownError")), {
        variant: "error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
        <TextField
          label={t("prediction:label.horizon")}
          helperText={t("prediction:label.horizonDescription")}
          type="number"
          size="small"
          value={horizon}
          onChange={(event) => setHorizon(event.target.value)}
          error={horizon !== "" && !isValid}
          slotProps={{ htmlInput: { min: 1, step: 1 } }}
          sx={{ width: 220 }}
        />
        <LoadingButton
          variant="contained"
          size="small"
          startIcon={<PlayArrowIcon />}
          onClick={handleRun}
          disabled={!isValid}
          loading={isSubmitting}
          sx={{ textTransform: "none", fontWeight: 500, mt: 0.5 }}
        >
          {t("prediction:button.runPrediction")}
        </LoadingButton>
      </Box>
      {warning && warning.horizon === steps && warning.unevaluated > 0 && (
        <Alert severity="warning">
          {t("prediction:message.unevaluatedSteps", {
            count: warning.unevaluated,
            evaluated: warning.evaluated,
          })}
        </Alert>
      )}
    </Box>
  );
}

HorizonPredictionPanel.propTypes = {
  run: PropTypes.shape({ id: PropTypes.number.isRequired }).isRequired,
  onSaved: PropTypes.func.isRequired,
};
