import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  AlertTitle,
  Box,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  Grid,
  Paper,
  Radio,
  RadioGroup,
  TextField,
  Typography,
} from "@mui/material";
import InfoIcon from "@mui/icons-material/Info";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";

import { getDatasetTemporalInfo } from "../../api/datasets";

/**
 * ForecastingOptions — child of PredictionModal.
 *
 * Renders when the experiment task is ForecastingTask.
 * Provides:
 *   1. Training-data time-series summary (frequency, date range, periods).
 *   2. Forecast mode selector:
 *      - "auto-generate"  → user enters the number of future periods.
 *      - "dataset"        → user picks a dataset (handled externally);
 *        this component validates its temporal frequency.
 *   3. Frequency-mismatch / match feedback when a prediction dataset is
 *      selected.
 *
 * Props
 * ─────
 * temporalInfo        — temporal metadata of the *training* dataset
 *                       (frequency_code, frequency_label, start_date, …).
 * forecastMode        — current mode ("auto-generate" | "dataset").
 * setForecastMode     — setter for mode.
 * forecastPeriods     — number of future periods (auto-generate mode).
 * setForecastPeriods  — setter for periods.
 * selectedDataset     — currently selected prediction dataset (or null).
 *                       When non-null and mode === "dataset", frequency
 *                       validation runs automatically.
 */
export default function ForecastingOptions({
  temporalInfo,
  forecastMode,
  setForecastMode,
  forecastPeriods,
  setForecastPeriods,
  selectedDataset,
}) {
  // ----- frequency validation state -----
  const [selectedDatasetTemporalInfo, setSelectedDatasetTemporalInfo] =
    useState(null);
  const [frequencyMismatch, setFrequencyMismatch] = useState(false);
  const [loadingTemporalInfo, setLoadingTemporalInfo] = useState(false);

  // Expose mismatch to parent via callback (so it can disable Submit)
  // We use the convention: parent reads `frequencyMismatch` via a ref or
  // the component simply blocks via canPredict logic in parent.

  // ----- validate temporal frequency of the selected prediction dataset -----
  useEffect(() => {
    const validateSelectedDatasetFrequency = async () => {
      if (!selectedDataset || forecastMode !== "dataset" || !temporalInfo) {
        setSelectedDatasetTemporalInfo(null);
        setFrequencyMismatch(false);
        return;
      }

      setLoadingTemporalInfo(true);
      try {
        const timestampColumn = temporalInfo.timestamp_column;
        const predictionDatasetInfo = await getDatasetTemporalInfo(
          selectedDataset.id,
          timestampColumn,
        );
        setSelectedDatasetTemporalInfo(predictionDatasetInfo);

        if (
          predictionDatasetInfo.frequency_code !== temporalInfo.frequency_code
        ) {
          setFrequencyMismatch(true);
        } else {
          setFrequencyMismatch(false);
        }
      } catch (error) {
        console.error("Error validating prediction dataset frequency:", error);
        setSelectedDatasetTemporalInfo(null);
        setFrequencyMismatch(false);
      } finally {
        setLoadingTemporalInfo(false);
      }
    };

    validateSelectedDatasetFrequency();
  }, [selectedDataset, forecastMode, temporalInfo]);

  // Reset validation when switching to auto-generate
  const handleModeChange = useCallback(
    (newMode) => {
      setForecastMode(newMode);
      if (newMode === "auto-generate") {
        setSelectedDatasetTemporalInfo(null);
        setFrequencyMismatch(false);
      } else {
        setForecastPeriods(null);
      }
    },
    [setForecastMode, setForecastPeriods],
  );

  if (!temporalInfo) return null;

  return (
    <Box sx={{ mb: 3 }}>
      {/* ── 1. Training data time-series summary ── */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 2,
          bgcolor: "success.50",
          border: "1px solid",
          borderColor: "success.200",
          borderRadius: 2,
        }}
      >
        <Typography
          variant="subtitle2"
          sx={{ mb: 1.5, display: "flex", alignItems: "center", gap: 1 }}
        >
          <TrendingUpIcon fontSize="small" color="success" />
          Training Data Time Series Properties
        </Typography>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <AccessTimeIcon fontSize="small" color="action" />
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Frequency
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  <Chip
                    label={temporalInfo.frequency_label}
                    size="small"
                    color="success"
                    sx={{ mr: 0.5 }}
                  />
                </Typography>
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CalendarTodayIcon fontSize="small" color="action" />
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Training Period
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {new Date(temporalInfo.start_date).toLocaleDateString()} →{" "}
                  {new Date(temporalInfo.end_date).toLocaleDateString()}
                </Typography>
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Training Periods
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {temporalInfo.total_periods}{" "}
                {temporalInfo.frequency_label.toLowerCase()}
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Average Interval
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {temporalInfo.average_interval}
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>What this means:</strong> The model was trained on{" "}
            <strong>{temporalInfo.frequency_label.toLowerCase()}</strong> data.
            Each prediction step will forecast{" "}
            <strong>
              1 {temporalInfo.frequency_label.toLowerCase().slice(0, -2)}
            </strong>{" "}
            into the future. {temporalInfo.frequency_example}
          </Typography>
        </Alert>
      </Paper>

      {/* ── 2. Forecast mode selector ── */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 2,
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 2,
        }}
      >
        <Typography variant="subtitle1" fontWeight="medium" sx={{ mb: 2 }}>
          Choose Prediction Method
        </Typography>

        <FormControl component="fieldset" fullWidth>
          <RadioGroup
            value={forecastMode}
            onChange={(e) => handleModeChange(e.target.value)}
          >
            {/* ── Auto-generate option ── */}
            <Paper
              elevation={0}
              sx={{
                p: 2,
                mb: 2,
                border: "2px solid",
                borderColor:
                  forecastMode === "auto-generate" ? "primary.main" : "divider",
                borderRadius: 2,
                bgcolor:
                  forecastMode === "auto-generate"
                    ? "primary.50"
                    : "transparent",
                cursor: "pointer",
              }}
              onClick={() => handleModeChange("auto-generate")}
            >
              <FormControlLabel
                value="auto-generate"
                control={<Radio />}
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <AutoAwesomeIcon
                      color={
                        forecastMode === "auto-generate" ? "primary" : "action"
                      }
                    />
                    <Box>
                      <Typography variant="subtitle2" fontWeight="medium">
                        Auto-generate Future Timestamps
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Automatically generate future dates from the last
                        training date.
                        {` Starting from ${new Date(temporalInfo.end_date).toLocaleDateString()}.`}
                      </Typography>
                    </Box>
                  </Box>
                }
                sx={{ m: 0, width: "100%" }}
              />

              {forecastMode === "auto-generate" && (
                <Box sx={{ mt: 2, pl: 4 }}>
                  <TextField
                    fullWidth
                    type="number"
                    size="small"
                    label={`Number of Future ${temporalInfo.frequency_label}`}
                    placeholder="e.g., 30"
                    value={forecastPeriods ?? ""}
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value === "") {
                        setForecastPeriods(null);
                      } else {
                        const numValue = parseInt(value, 10);
                        if (numValue > 0 && numValue <= 1000) {
                          setForecastPeriods(numValue);
                        }
                      }
                    }}
                    helperText={`Forecast ${forecastPeriods || "N"} ${temporalInfo.frequency_label.toLowerCase()} into the future`}
                    inputProps={{ min: 1, max: 1000 }}
                  />
                  <Alert severity="warning" sx={{ mt: 1 }} icon={<InfoIcon />}>
                    <Typography variant="body2">
                      This option is <strong>not available</strong> for models
                      trained with exogenous variables, as future values of
                      those variables are required.
                    </Typography>
                  </Alert>
                </Box>
              )}
            </Paper>

            {/* ── Upload-dataset option ── */}
            <Paper
              elevation={0}
              sx={{
                p: 2,
                border: "2px solid",
                borderColor:
                  forecastMode === "dataset" ? "primary.main" : "divider",
                borderRadius: 2,
                bgcolor:
                  forecastMode === "dataset" ? "primary.50" : "transparent",
                cursor: "pointer",
              }}
              onClick={() => handleModeChange("dataset")}
            >
              <FormControlLabel
                value="dataset"
                control={<Radio />}
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <UploadFileIcon
                      color={forecastMode === "dataset" ? "primary" : "action"}
                    />
                    <Box>
                      <Typography variant="subtitle2" fontWeight="medium">
                        Upload Dataset with Timestamps
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Use a dataset containing specific timestamps you want to
                        predict. Required if the model uses exogenous variables.
                      </Typography>
                    </Box>
                  </Box>
                }
                sx={{ m: 0, width: "100%" }}
              />
            </Paper>
          </RadioGroup>
        </FormControl>
      </Paper>

      {/* ── 3. Dataset requirements info (only in dataset mode) ── */}
      {forecastMode === "dataset" && (
        <Alert severity="info" icon={<InfoIcon />} sx={{ mb: 2 }}>
          <AlertTitle>Dataset Requirements</AlertTitle>
          <Typography variant="body2" component="div">
            <strong>For forecasting predictions:</strong>
            <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
              <li>
                Dataset must include a <strong>ds</strong> (timestamp) column
                with dates to predict (past, present, or future)
              </li>
              <li>
                Timestamps must be <strong>strictly increasing</strong> and
                match the training frequency
                <strong> ({temporalInfo.frequency_label})</strong>
              </li>
              <li>
                If the model used exogenous regressors during training, include
                those columns with values for all timestamps
              </li>
              <li>
                Any <strong>y</strong> (target) column will be ignored during
                prediction
              </li>
            </ul>
          </Typography>
        </Alert>
      )}

      {/* ── 4. Frequency validation feedback ── */}

      {/* Loading spinner */}
      {forecastMode === "dataset" && loadingTemporalInfo && selectedDataset && (
        <Box sx={{ mt: 1, display: "flex", alignItems: "center", gap: 1 }}>
          <CircularProgress size={16} />
          <Typography variant="body2" color="text.secondary">
            Validating dataset temporal frequency…
          </Typography>
        </Box>
      )}

      {/* Mismatch error */}
      {forecastMode === "dataset" &&
        frequencyMismatch &&
        selectedDatasetTemporalInfo &&
        temporalInfo && (
          <Alert severity="error" icon={<WarningAmberIcon />} sx={{ mt: 1 }}>
            <AlertTitle>Temporal Frequency Mismatch</AlertTitle>
            <Typography variant="body2" component="div">
              The selected dataset has a{" "}
              <strong>different temporal frequency</strong> than the training
              data:
              <Box sx={{ mt: 1, display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Training Data
                  </Typography>
                  <Box>
                    <Chip
                      label={temporalInfo.frequency_label}
                      size="small"
                      color="success"
                      sx={{ mr: 0.5 }}
                    />
                    <Typography variant="caption">
                      ({temporalInfo.average_interval})
                    </Typography>
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Selected Dataset
                  </Typography>
                  <Box>
                    <Chip
                      label={selectedDatasetTemporalInfo.frequency_label}
                      size="small"
                      color="error"
                      sx={{ mr: 0.5 }}
                    />
                    <Typography variant="caption">
                      ({selectedDatasetTemporalInfo.average_interval})
                    </Typography>
                  </Box>
                </Box>
              </Box>
              <Typography variant="body2" sx={{ mt: 1 }}>
                <strong>This will produce incorrect predictions.</strong> Please
                select a dataset with{" "}
                <strong>{temporalInfo.frequency_label.toLowerCase()}</strong>{" "}
                frequency, or use the auto-generate option above.
              </Typography>
            </Typography>
          </Alert>
        )}

      {/* Success match */}
      {forecastMode === "dataset" &&
        !frequencyMismatch &&
        selectedDatasetTemporalInfo &&
        temporalInfo &&
        !loadingTemporalInfo && (
          <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mt: 1 }}>
            <Typography variant="body2">
              <strong>Frequency match!</strong> The selected dataset has the
              same temporal frequency (
              <strong>{selectedDatasetTemporalInfo.frequency_label}</strong>) as
              the training data. Period:{" "}
              {new Date(
                selectedDatasetTemporalInfo.start_date,
              ).toLocaleDateString()}{" "}
              →{" "}
              {new Date(
                selectedDatasetTemporalInfo.end_date,
              ).toLocaleDateString()}{" "}
              ({selectedDatasetTemporalInfo.total_periods} periods)
            </Typography>
          </Alert>
        )}
    </Box>
  );
}

/** Whether the current forecasting configuration blocks prediction. */
ForecastingOptions.isBlocked = ({
  forecastMode,
  forecastPeriods,
  selectedDataset,
  frequencyMismatch,
}) => {
  if (forecastMode === "auto-generate") {
    return !forecastPeriods || forecastPeriods <= 0;
  }
  // dataset mode
  if (!selectedDataset) return true;
  if (frequencyMismatch) return true;
  return false;
};

ForecastingOptions.propTypes = {
  temporalInfo: PropTypes.shape({
    frequency_code: PropTypes.string,
    frequency_label: PropTypes.string,
    frequency_description: PropTypes.string,
    frequency_example: PropTypes.string,
    average_interval: PropTypes.string,
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    total_periods: PropTypes.number,
    detected_gaps: PropTypes.number,
    timestamp_column: PropTypes.string,
  }),
  forecastMode: PropTypes.oneOf(["auto-generate", "dataset"]).isRequired,
  setForecastMode: PropTypes.func.isRequired,
  forecastPeriods: PropTypes.number,
  setForecastPeriods: PropTypes.func.isRequired,
  selectedDataset: PropTypes.object,
};
