import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  Grid,
  TextField,
  Typography,
  FormHelperText,
  Slider,
  Box,
  Alert,
  AlertTitle,
  Chip,
  CircularProgress,
  Paper,
  Collapse,
} from "@mui/material";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";

/**
 * Component for temporal splitting of time series data for forecasting tasks.
 * Unlike random splitting, this maintains temporal order to prevent data leakage.
 */
function SplitDatasetTemporal({
  datasetInfo,
  rowsPartitionsPercentage,
  setRowsPartitionsPercentage,
  setSplitsReady,
  gap,
  setGap,
  temporalInfo,
  temporalInfoLoading,
}) {
  const totalRows = datasetInfo.total_rows;

  const [splitError, setSplitError] = useState(false);
  const [splitErrorText, setSplitErrorText] = useState("");

  // Minimum sizes for temporal splits - scaled based on dataset size
  // For small datasets (testing/demo), use proportional minimums
  const isSmallDataset = totalRows < 100;
  const MIN_TRAIN_SIZE = isSmallDataset
    ? Math.max(3, Math.floor(totalRows * 0.5))
    : 50;
  const MIN_VAL_SIZE = isSmallDataset
    ? Math.max(1, Math.floor(totalRows * 0.15))
    : 10;
  const MIN_TEST_SIZE = isSmallDataset
    ? Math.max(1, Math.floor(totalRows * 0.15))
    : 10;

  const checkTemporalSplit = (train, validation, test, gapValue) => {
    // Convert percentages to actual row counts
    const trainRows = Math.floor(totalRows * train);
    const valRows = Math.floor(totalRows * validation);
    const testRows = Math.floor(totalRows * test);

    // Total rows needed including gaps
    const totalNeeded = trainRows + valRows + testRows + 2 * gapValue;

    if (totalNeeded > totalRows) {
      setSplitErrorText(
        `Not enough data. Need ${totalNeeded} rows but have ${totalRows}. Try reducing gap or split sizes.`,
      );
      return false;
    }

    if (trainRows < MIN_TRAIN_SIZE) {
      setSplitErrorText(
        `Training set too small: ${trainRows} < ${MIN_TRAIN_SIZE}. Increase train proportion.`,
      );
      return false;
    }

    if (valRows < MIN_VAL_SIZE) {
      setSplitErrorText(
        `Validation set too small: ${valRows} < ${MIN_VAL_SIZE}. Increase validation proportion.`,
      );
      return false;
    }

    if (testRows < MIN_TEST_SIZE) {
      setSplitErrorText(
        `Test set too small: ${testRows} < ${MIN_TEST_SIZE}. Increase test proportion.`,
      );
      return false;
    }

    // Use tolerance for floating point comparison (0.7 + 0.2 + 0.1 !== 1 in JS)
    const sum = train + validation + test;
    if (Math.abs(sum - 1) > 0.0001) {
      setSplitErrorText(
        "Splits should be numbers between 0 and 1 and should add 1 in total",
      );
      return false;
    }

    return true;
  };

  const handleRowsChange = (event) => {
    const value = parseFloat(event.target.value);
    const id = event.target.id;

    let newSplit = { ...rowsPartitionsPercentage };
    switch (id) {
      case "train":
        newSplit = { ...newSplit, train: value };
        break;
      case "validation":
        newSplit = { ...newSplit, validation: value };
        break;
      case "test":
        newSplit = { ...newSplit, test: value };
        break;
    }

    setRowsPartitionsPercentage(newSplit);

    if (
      !checkTemporalSplit(
        newSplit.train,
        newSplit.validation,
        newSplit.test,
        gap,
      )
    ) {
      setSplitError(true);
    } else {
      setSplitError(false);
      setSplitErrorText("");
    }
  };

  const handleGapChange = (event, newValue) => {
    setGap(newValue);

    if (
      !checkTemporalSplit(
        rowsPartitionsPercentage.train,
        rowsPartitionsPercentage.validation,
        rowsPartitionsPercentage.test,
        newValue,
      )
    ) {
      setSplitError(true);
    } else {
      setSplitError(false);
      setSplitErrorText("");
    }
  };

  useEffect(() => {
    // Validate splits on mount and when data changes
    // Ensure we have dataset info before validating
    if (!totalRows || totalRows <= 0) {
      setSplitsReady(false);
      return;
    }

    const isValid =
      !splitError &&
      rowsPartitionsPercentage.train > 0 &&
      rowsPartitionsPercentage.validation > 0 &&
      rowsPartitionsPercentage.test > 0 &&
      checkTemporalSplit(
        rowsPartitionsPercentage.train,
        rowsPartitionsPercentage.validation,
        rowsPartitionsPercentage.test,
        gap,
      );

    setSplitsReady(isValid);
  }, [rowsPartitionsPercentage, splitError, gap, totalRows]);

  // Calculate actual row numbers for display
  const trainRows = Math.floor(totalRows * rowsPartitionsPercentage.train);
  const valRows = Math.floor(totalRows * rowsPartitionsPercentage.validation);
  const testRows = Math.floor(totalRows * rowsPartitionsPercentage.test);

  // Format date for display
  const formatDate = (isoString) => {
    if (!isoString) return "";
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <React.Fragment>
      <Grid container spacing={1}>
        {/* Temporal Information Panel */}
        <Grid size={{ xs: 12 }}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              mb: 2,
              bgcolor: "primary.50",
              border: "1px solid",
              borderColor: "primary.200",
              borderRadius: 2,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{ mb: 1.5, display: "flex", alignItems: "center", gap: 1 }}
            >
              <TrendingUpIcon fontSize="small" color="primary" />
              Detected Time Series Properties
            </Typography>

            {temporalInfoLoading ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <CircularProgress size={16} />
                <Typography variant="body2" color="text.secondary">
                  Analyzing temporal patterns...
                </Typography>
              </Box>
            ) : temporalInfo ? (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
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
                          color="primary"
                          sx={{ mr: 0.5 }}
                        />
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {temporalInfo.frequency_description}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>

                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <CalendarTodayIcon fontSize="small" color="action" />
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Date Range
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {formatDate(temporalInfo.start_date)} →{" "}
                        {formatDate(temporalInfo.end_date)}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>

                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Total Periods
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {temporalInfo.total_periods} data points
                    </Typography>
                  </Box>
                </Grid>

                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Average Interval
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {temporalInfo.average_interval}
                    </Typography>
                    {temporalInfo.detected_gaps > 0 && (
                      <Typography variant="caption" color="warning.main">
                        ⚠️ {temporalInfo.detected_gaps} gaps detected
                      </Typography>
                    )}
                  </Box>
                </Grid>

                <Grid size={{ xs: 12 }}>
                  <Alert severity="info" sx={{ mt: 1 }}>
                    <Typography variant="body2">
                      <strong>Prediction interpretation:</strong> When you
                      forecast {gap > 0 ? `with a ${gap} period gap` : ""}, each
                      prediction step represents{" "}
                      <strong>
                        1{" "}
                        {temporalInfo.frequency_label
                          .toLowerCase()
                          .slice(0, -2)}
                      </strong>
                      . {temporalInfo.frequency_example}
                    </Typography>
                  </Alert>
                </Grid>
              </Grid>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Select an input column (timestamp) to analyze temporal
                properties.
              </Typography>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            <AlertTitle>Temporal Splitting for Time Series</AlertTitle>
            <Typography variant="body2">
              For forecasting tasks, data is split chronologically to prevent
              data leakage:
            </Typography>
            <ul style={{ marginTop: 8, marginBottom: 0 }}>
              <li>Training data comes first (oldest)</li>
              <li>Validation data follows training data</li>
              <li>Test data comes last (most recent)</li>
              <li>
                Optional gap between splits to simulate real-world scenarios
              </li>
            </ul>
          </Alert>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 2 }}>
            Select proportions for temporal splits
          </Typography>
        </Grid>
      </Grid>

      <Grid container direction="row" spacing={4}>
        <Grid size={{ xs: 4 }}>
          <TextField
            id="train"
            label="Train"
            autoComplete="off"
            type="number"
            size="small"
            error={splitError}
            value={rowsPartitionsPercentage.train}
            onChange={handleRowsChange}
            inputProps={{ step: 0.05, min: 0, max: 1 }}
            helperText={`~${trainRows} ${temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"}`}
          />
        </Grid>
        <Grid size={{ xs: 4 }}>
          <TextField
            id="validation"
            label="Validation"
            autoComplete="off"
            type="number"
            size="small"
            error={splitError}
            value={rowsPartitionsPercentage.validation}
            onChange={handleRowsChange}
            inputProps={{ step: 0.05, min: 0, max: 1 }}
            helperText={`~${valRows} ${temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"}`}
          />
        </Grid>
        <Grid size={{ xs: 4 }}>
          <TextField
            id="test"
            label="Test"
            type="number"
            size="small"
            autoComplete="off"
            error={splitError}
            value={rowsPartitionsPercentage.test}
            onChange={handleRowsChange}
            inputProps={{ step: 0.05, min: 0, max: 1 }}
            helperText={`~${testRows} ${temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"}`}
          />
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Box sx={{ mt: 2, mb: 1 }}>
            <Typography gutterBottom>
              Gap between splits{" "}
              {temporalInfo
                ? `(${temporalInfo.frequency_label.toLowerCase()} to skip)`
                : "(periods to skip)"}
            </Typography>
            <Slider
              value={gap}
              onChange={handleGapChange}
              min={0}
              max={Math.floor(totalRows * 0.1)} // Max 10% of dataset
              step={1}
              marks={[
                { value: 0, label: "0" },
                {
                  value: Math.floor(totalRows * 0.05),
                  label: `${Math.floor(totalRows * 0.05)}`,
                },
                {
                  value: Math.floor(totalRows * 0.1),
                  label: `${Math.floor(totalRows * 0.1)}`,
                },
              ]}
              valueLabelDisplay="auto"
            />
            <Typography variant="caption" color="textSecondary">
              Gap helps simulate real-world forecasting by adding delay between
              training and prediction.
              {temporalInfo && (
                <>
                  {" "}
                  Current gap: <strong>{gap}</strong>{" "}
                  {temporalInfo.frequency_label.toLowerCase()}.
                </>
              )}
            </Typography>
          </Box>
        </Grid>
      </Grid>

      {splitError && (
        <FormHelperText error sx={{ mt: 2 }}>
          {splitErrorText}
        </FormHelperText>
      )}

      <Box sx={{ mt: 2 }}>
        <Typography variant="body2" color="textSecondary">
          <strong>Timeline preview:</strong> Train ({trainRows}{" "}
          {temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"})
          {gap > 0 &&
            ` → Gap (${gap} ${temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"})`}{" "}
          → Validation ({valRows}{" "}
          {temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"})
          {gap > 0 &&
            ` → Gap (${gap} ${temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"})`}{" "}
          → Test ({testRows}{" "}
          {temporalInfo ? temporalInfo.frequency_label.toLowerCase() : "rows"})
        </Typography>
      </Box>

      {/* Small Dataset Warnings for Forecasting */}
      <Collapse in={totalRows < 50}>
        <Alert severity="warning" sx={{ mt: 2 }} icon={<WarningAmberIcon />}>
          <AlertTitle>Small Dataset Detected ({totalRows} rows)</AlertTitle>
          <Typography variant="body2" sx={{ mb: 1 }}>
            Your dataset is relatively small for time series forecasting. This
            may affect model performance:
          </Typography>
          <Box component="ul" sx={{ mt: 1, mb: 1, pl: 2 }}>
            {trainRows < 10 && (
              <li>
                <Typography variant="body2">
                  <strong>Training set ({trainRows} rows):</strong> Some models
                  may auto-adjust their parameters (e.g., reduced lag window,
                  disabled seasonality) to work with limited data.
                </Typography>
              </li>
            )}
            {valRows < 5 && (
              <li>
                <Typography variant="body2">
                  <strong>Validation set ({valRows} rows):</strong> Very small
                  validation sets may result in unreliable or NaN metrics.
                  Consider increasing validation proportion.
                </Typography>
              </li>
            )}
            {testRows < 5 && (
              <li>
                <Typography variant="body2">
                  <strong>Test set ({testRows} rows):</strong> Very small test
                  sets may not provide meaningful evaluation metrics.
                </Typography>
              </li>
            )}
            {totalRows < 20 && (
              <li>
                <Typography variant="body2">
                  <strong>Seasonal models (SARIMAX):</strong> Seasonality will
                  be automatically disabled as there isn&apos;t enough data to
                  detect seasonal patterns.
                </Typography>
              </li>
            )}
          </Box>
          <Typography variant="body2" color="text.secondary">
            💡 <strong>Tip:</strong> For best results, time series models
            typically need at least 50-100 data points. With small datasets,
            simpler models like <strong>SklearnMultiStepForecaster</strong>{" "}
            often perform better than complex ones.
          </Typography>
        </Alert>
      </Collapse>
    </React.Fragment>
  );
}

SplitDatasetTemporal.propTypes = {
  datasetInfo: PropTypes.shape({
    total_rows: PropTypes.number,
  }).isRequired,
  rowsPartitionsPercentage: PropTypes.shape({
    train: PropTypes.number,
    validation: PropTypes.number,
    test: PropTypes.number,
  }).isRequired,
  setRowsPartitionsPercentage: PropTypes.func.isRequired,
  setSplitsReady: PropTypes.func.isRequired,
  gap: PropTypes.number.isRequired,
  setGap: PropTypes.func.isRequired,
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
  temporalInfoLoading: PropTypes.bool,
};

SplitDatasetTemporal.defaultProps = {
  temporalInfo: null,
  temporalInfoLoading: false,
};

export default SplitDatasetTemporal;
