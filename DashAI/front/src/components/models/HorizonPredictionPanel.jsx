import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { LoadingButton } from "@mui/lab";
import { PlayArrow as PlayArrowIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import {
  createPrediction,
  getFutureDates,
  getPredictionSplits,
  getPredictions,
} from "../../api/predict";
import DatasetPredictionPanel from "./DatasetPredictionPanel";
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
 *
 * A run that read exogenous variables declares their columns (`exogenous`)
 * and forecasts their future values instead: from a dataset of the future
 * rows, or typed in on the next dates of its grid, which the backend gives.
 * The horizon is then the number of rows, and the warning belongs to them: to
 * the dataset chosen, or to as many rows as were typed in.
 */

// Exogenous columns of these types are typed in as numbers.
const NUMERIC_TYPES = ["Float", "Integer"];

export default function HorizonPredictionPanel({ run, onSaved }) {
  const { t } = useTranslation(["prediction", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const [horizon, setHorizon] = useState("");
  // The warning of the last prediction asked for, with what it was asked
  // for: { horizon } here, { mode: "manual", rows } or { mode: "dataset",
  // datasetId } for a run that read exogenous variables; plus { unevaluated,
  // evaluated }, as POST /predict/ answered.
  const [warning, setWarning] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // The columns a run that read exogenous variables needs the future of.
  const [exogenous, setExogenous] = useState(null);
  const [mode, setMode] = useState("dataset");
  // The future typed in by hand: one row per date the backend gave.
  const [timeIndex, setTimeIndex] = useState(null);
  const [futureRows, setFutureRows] = useState([]);
  const datasetRunRef = useRef(null);
  const [datasetRunState, setDatasetRunState] = useState({
    canRun: false,
    isSubmitting: false,
    datasetId: null,
  });

  useEffect(() => {
    let cancelled = false;
    getPredictionSplits(run.id)
      .then(({ horizon: measured, exogenous: declared }) => {
        if (cancelled) return;
        if (measured) setHorizon((current) => current || String(measured));
        setExogenous(declared ?? null);
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

  const columns = exogenous?.columns ?? [];
  // How many rows the backend takes typed in: past it the form would freeze
  // drawing a field per row and column, and the rows come in a dataset.
  const maxRows = exogenous?.max_rows ?? null;
  const tooMany = maxRows !== null && isValid && steps > maxRows;
  const typedIn = futureRows.length > 0;
  const allTyped =
    typedIn &&
    futureRows.every((row) =>
      columns.every((column) => String(row[column.name] ?? "") !== ""),
    );

  const handleGenerateDates = async () => {
    try {
      const { timeIndex: column, dates } = await getFutureDates(run.id, steps);
      setTimeIndex(column);
      setFutureRows(dates.map((date) => ({ [column]: date })));
    } catch (error) {
      enqueueSnackbar(getApiErrorMessage(error, t("common:unknownError")), {
        variant: "error",
      });
    }
  };

  const setValue = (index, name, value) =>
    setFutureRows((rows) =>
      rows.map((row, i) => (i === index ? { ...row, [name]: value } : row)),
    );

  // The rows as the job reads them: numbers where the column is numeric.
  const manualInput = () =>
    futureRows.map((row) => {
      const typed = { [timeIndex]: row[timeIndex] };
      columns.forEach((column) => {
        const value = row[column.name];
        typed[column.name] = NUMERIC_TYPES.includes(column.type)
          ? Number(value)
          : value;
      });
      return typed;
    });

  const answered = (prediction) => ({
    unevaluated: prediction.unevaluated_steps ?? 0,
    evaluated: prediction.evaluated_horizon ?? null,
  });

  const handleRun = async () => {
    setIsSubmitting(true);
    try {
      // With exogenous variables the horizon is the number of rows typed in.
      const asked = exogenous ? futureRows.length : steps;
      const prediction = await createPrediction(run.id, null, null, asked);
      setWarning(
        exogenous
          ? { mode: "manual", rows: asked, ...answered(prediction) }
          : { horizon: asked, ...answered(prediction) },
      );
      const jobResponse = exogenous
        ? await enqueuePredictionJob(prediction.id, manualInput())
        : await enqueuePredictionJob(prediction.id);
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

  // The warning shows while the form still holds what it was asked for.
  const warningHolds =
    warning &&
    warning.unevaluated > 0 &&
    (exogenous
      ? warning.mode === mode &&
        (mode === "manual"
          ? warning.rows === futureRows.length
          : warning.datasetId === datasetRunState.datasetId)
      : warning.horizon === steps);
  const warningAlert = warningHolds && (
    <Alert severity="warning">
      {t("prediction:message.unevaluatedSteps", {
        count: warning.unevaluated,
        evaluated: warning.evaluated,
      })}
    </Alert>
  );

  const runButton = (onClick, disabled, loading) => (
    <LoadingButton
      variant="contained"
      size="small"
      startIcon={<PlayArrowIcon />}
      onClick={onClick}
      disabled={disabled}
      loading={loading}
      sx={{ textTransform: "none", fontWeight: 500, alignSelf: "flex-start" }}
    >
      {t("prediction:button.runPrediction")}
    </LoadingButton>
  );

  if (exogenous) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {t("prediction:message.exogenousFuture", {
            columns: columns.map((column) => column.name).join(", "),
          })}
        </Typography>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={mode}
          onChange={(event, value) => value && setMode(value)}
        >
          <ToggleButton value="dataset" sx={{ textTransform: "none" }}>
            {t("prediction:label.futureFromDataset")}
          </ToggleButton>
          <ToggleButton value="manual" sx={{ textTransform: "none" }}>
            {t("prediction:label.futureTypedIn")}
          </ToggleButton>
        </ToggleButtonGroup>
        {mode === "dataset" ? (
          // The top padding keeps the selector's outlined label, which sits
          // above the field, off the mode buttons.
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
            <DatasetPredictionPanel
              run={run}
              onSaved={onSaved}
              onClose={() => {}}
              runRef={datasetRunRef}
              onStateChange={setDatasetRunState}
              onCreated={(prediction) =>
                setWarning({
                  mode: "dataset",
                  datasetId: prediction.dataset_id ?? null,
                  ...answered(prediction),
                })
              }
            />
            {runButton(
              () => datasetRunRef.current?.(),
              !datasetRunState.canRun,
              datasetRunState.isSubmitting,
            )}
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
              <TextField
                label={t("prediction:label.horizon")}
                helperText={
                  tooMany
                    ? t("prediction:label.futureStepsMax", { max: maxRows })
                    : t("prediction:label.futureStepsDescription")
                }
                type="number"
                size="small"
                value={horizon}
                onChange={(event) => setHorizon(event.target.value)}
                error={(horizon !== "" && !isValid) || tooMany}
                slotProps={{
                  htmlInput: { min: 1, step: 1, max: maxRows ?? undefined },
                }}
                sx={{ width: 220 }}
              />
              <Button
                variant="outlined"
                size="small"
                onClick={handleGenerateDates}
                disabled={!isValid || tooMany}
                sx={{ textTransform: "none", mt: 0.5 }}
              >
                {t("prediction:button.generateDates")}
              </Button>
            </Box>
            {futureRows.map((row, index) => (
              <Box
                key={row[timeIndex]}
                sx={{ display: "flex", alignItems: "center", gap: 2 }}
              >
                <Typography variant="body2" sx={{ width: 140 }}>
                  {row[timeIndex]}
                </Typography>
                {columns.map((column) => (
                  <TextField
                    key={column.name}
                    label={column.name}
                    size="small"
                    type={
                      NUMERIC_TYPES.includes(column.type) ? "number" : "text"
                    }
                    value={row[column.name] ?? ""}
                    onChange={(event) =>
                      setValue(index, column.name, event.target.value)
                    }
                    slotProps={{
                      htmlInput: {
                        "aria-label": `${column.name} ${row[timeIndex]}`,
                      },
                    }}
                  />
                ))}
              </Box>
            ))}
            {typedIn && runButton(handleRun, !allTyped, isSubmitting)}
          </Box>
        )}
        {warningAlert}
      </Box>
    );
  }

  return (
    // The top padding leaves room for the outlined field's label, which sits
    // above the field and was cut by the tab's scroll container.
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
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
      {warningAlert}
    </Box>
  );
}

HorizonPredictionPanel.propTypes = {
  run: PropTypes.shape({ id: PropTypes.number.isRequired }).isRequired,
  onSaved: PropTypes.func.isRequired,
};
