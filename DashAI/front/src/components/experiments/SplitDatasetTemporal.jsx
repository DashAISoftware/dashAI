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
} from "@mui/material";

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
}) {
  const totalRows = datasetInfo.total_rows;

  const [splitError, setSplitError] = useState(false);
  const [splitErrorText, setSplitErrorText] = useState("");

  // Minimum sizes for temporal splits
  const MIN_TRAIN_SIZE = 50;
  const MIN_VAL_SIZE = 10;
  const MIN_TEST_SIZE = 10;

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

    if (train + validation + test !== 1) {
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

  return (
    <React.Fragment>
      <Grid container spacing={1}>
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
            helperText={`~${trainRows} rows`}
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
            helperText={`~${valRows} rows`}
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
            helperText={`~${testRows} rows`}
          />
        </Grid>

        <Grid size={{ xs: 12 }}>
          <Box sx={{ mt: 2, mb: 1 }}>
            <Typography gutterBottom>
              Gap between splits (number of periods to skip)
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
              training and prediction. Use 0 for no gap.
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
          <strong>Timeline preview:</strong> Train (rows 0-{trainRows - 1})
          {gap > 0 && ` → Gap (${gap} rows)`} → Validation (rows{" "}
          {trainRows + gap}-{trainRows + gap + valRows - 1})
          {gap > 0 && ` → Gap (${gap} rows)`} → Test (rows{" "}
          {trainRows + gap + valRows + gap}-
          {trainRows + gap + valRows + gap + testRows - 1})
        </Typography>
      </Box>
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
};

export default SplitDatasetTemporal;
