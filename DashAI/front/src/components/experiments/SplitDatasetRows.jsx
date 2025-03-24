import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { parseRangeToIndex } from "../../utils/parseRange";
import {
  Grid,
  TextField,
  Typography,
  FormControlLabel,
  Radio,
  RadioGroup,
  FormHelperText,
} from "@mui/material";
import BooleanInput from "../configurableObject/Inputs/BooleanInput";

function SplitDatasetRows({
  datasetInfo,
  rowsPartitionsIndex,
  setRowsPartitionsIndex,
  rowsPartitionsPercentage,
  setRowsPartitionsPercentage,
  setSplitsReady,
  splitType,
  setSplitType,
  SPLIT_TYPES,
  shuffle,
  setShuffle,
  stratify,
  setStratify,
  seed,
  setSeed,
}) {
  const totalRows = datasetInfo.total_rows;
  const trainDatasetPercentage = (datasetInfo.train_size / totalRows).toFixed(
    2,
  );
  const validationDatasetPercentage = (
    datasetInfo.val_size / totalRows
  ).toFixed(2);
  const testDatasetPercentage = (datasetInfo.test_size / totalRows).toFixed(2);

  const hasPredefinedSplits =
    trainDatasetPercentage > 0 ||
    validationDatasetPercentage > 0 ||
    testDatasetPercentage > 0;

  const checkSplit = (train, validation, test) => {
    return train + validation + test === 1;
  };

  // handle rows numbers change state
  const disabledTextFieldStyle = {
    "& .MuiInputBase-input.Mui-disabled": {
      WebkitTextFillColor: "#999",
    },
    "& .MuiInputLabel-root.Mui-disabled": {
      color: "#bbb",
    },
  };
  const [rowsPartitionsError, setRowsPartitionsError] = useState(false);
  const [rowsPartitionsErrorText, setRowsPartitionsErrorText] = useState("");

  const handleSplitTypeChange = (event) => {
    const newType = event.target.value;
    setSplitType(newType);

    if (newType === SPLIT_TYPES.PREDEFINED) {
      setRowsPartitionsError(false);
      setSplitsReady(true);
    }
    if (newType === SPLIT_TYPES.RANDOM) {
      setSplitType(newType);
      setRowsPartitionsPercentage({ train: 0.6, test: 0.2, validation: 0.2 });
    }
    if (newType === SPLIT_TYPES.MANUAL) {
      setSplitType(newType);
      setRowsPartitionsIndex({ train: [], test: [], validation: [] });
    }
  };

  const handleRowsChange = (event) => {
    const value = event.target.value;
    const id = event.target.id; // TODO: check that the training, validation and testing rows dont overlap
    if (splitType === SPLIT_TYPES.MANUAL) {
      try {
        const rowsIndex = parseRangeToIndex(value, totalRows);
        switch (id) {
          case "train":
            setRowsPartitionsIndex({
              ...rowsPartitionsIndex,
              train: rowsIndex,
            });
            break;
          case "validation":
            setRowsPartitionsIndex({
              ...rowsPartitionsIndex,
              validation: rowsIndex,
            });
            break;
          case "test":
            setRowsPartitionsIndex({
              ...rowsPartitionsIndex,
              test: rowsIndex,
            });
            break;
        }
        setRowsPartitionsError(false);
      } catch (error) {
        setRowsPartitionsErrorText(error.message);
        setRowsPartitionsError(true);
      }
    } else {
      let newSplit = rowsPartitionsPercentage;
      switch (id) {
        case "train":
          newSplit = { ...newSplit, train: parseFloat(value) };
          break;
        case "validation":
          newSplit = { ...newSplit, validation: parseFloat(value) };
          break;
        case "test":
          newSplit = { ...newSplit, test: parseFloat(value) };
          break;
      }
      setRowsPartitionsPercentage(newSplit);
      if (!checkSplit(newSplit.train, newSplit.validation, newSplit.test)) {
        setRowsPartitionsErrorText(
          "Splits should be numbers between 0 and 1 and should add 1 in total",
        );
        setRowsPartitionsError(true);
      } else {
        setRowsPartitionsError(false);
      }
    }
  };

  const handleShuffleChange = (value) => {
    setShuffle(value);
    if (!value) {
      setStratify(false);
    }
  };

  const handleStratifyChange = (value) => {
    if (shuffle) {
      setStratify(value);
    } else {
      setStratify(false);
    }
  };

  const handleSeedChange = (event) => {
    setSeed(event.target.value);
  };

  useEffect(() => {
    if (hasPredefinedSplits) {
      setSplitType(SPLIT_TYPES.PREDEFINED);
    } else {
      setSplitType(SPLIT_TYPES.RANDOM);
    }
  }, [hasPredefinedSplits]);

  useEffect(() => {
    // check if splits doesnt have errors and arent empty
    if (splitType === SPLIT_TYPES.PREDEFINED) {
      setSplitsReady(true);
    } else if (
      splitType === SPLIT_TYPES.MANUAL &&
      !rowsPartitionsError &&
      rowsPartitionsIndex.train.length >= 1 &&
      rowsPartitionsIndex.validation.length >= 1 &&
      rowsPartitionsIndex.test.length >= 1
    ) {
      setSplitsReady(true);
    } else if (
      splitType === SPLIT_TYPES.RANDOM &&
      !rowsPartitionsError &&
      rowsPartitionsPercentage.train > 0 &&
      rowsPartitionsPercentage.validation > 0 &&
      rowsPartitionsPercentage.test > 0
    ) {
      setSplitsReady(true);
    } else {
      setSplitsReady(false);
    }
  }, [
    rowsPartitionsIndex,
    rowsPartitionsPercentage,
    rowsPartitionsError,
    splitType,
  ]);

  return (
    <React.Fragment>
      <Grid container spacing={1}>
        <Grid item xs={12}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 2 }}>
            Select how to divide the dataset into training, validation and test
            subsets.
          </Typography>
        </Grid>
      </Grid>
      <RadioGroup
        value={splitType}
        onChange={handleSplitTypeChange}
        name="radio-buttons-group"
      >
        <FormControlLabel
          value={SPLIT_TYPES.PREDEFINED}
          control={<Radio />}
          label={
            hasPredefinedSplits
              ? "Use predefined splits from dataset"
              : "Use predefined splits from dataset (not available)"
          }
          sx={{ my: 1 }}
          disabled={!hasPredefinedSplits}
        />
        {splitType === SPLIT_TYPES.PREDEFINED && (
          <Grid container direction="row" spacing={4}>
            <Grid item xs={4}>
              <TextField
                id="train"
                label="Train"
                value={trainDatasetPercentage}
                autoComplete="off"
                type="number"
                size="small"
                disabled
                sx={disabledTextFieldStyle}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                id="val"
                label="Validation"
                value={validationDatasetPercentage}
                disabled
                autoComplete="off"
                type="number"
                size="small"
                sx={disabledTextFieldStyle}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                id="test"
                label="Test"
                value={testDatasetPercentage}
                autoComplete="off"
                type="number"
                size="small"
                disabled
                sx={disabledTextFieldStyle}
              />
            </Grid>
          </Grid>
        )}
        <FormControlLabel
          value={SPLIT_TYPES.RANDOM}
          control={<Radio />}
          label="Use random rows by specifying which portion of the dataset you want to use for each subset"
          sx={{ my: 1 }}
        />
        <React.Fragment>
          {splitType === SPLIT_TYPES.RANDOM && (
            <Grid container direction="row" spacing={4}>
              <Grid item xs={4}>
                <TextField
                  id="train"
                  label="Train"
                  autoComplete="off"
                  type="number"
                  size="small"
                  error={rowsPartitionsError}
                  defaultValue={rowsPartitionsPercentage.train}
                  onChange={handleRowsChange}
                />
              </Grid>
              <Grid item xs={4}>
                <TextField
                  id="validation"
                  label="Validation"
                  autoComplete="off"
                  type="number"
                  size="small"
                  error={rowsPartitionsError}
                  defaultValue={rowsPartitionsPercentage.validation}
                  onChange={handleRowsChange}
                />
              </Grid>
              <Grid item xs={4}>
                <TextField
                  id="test"
                  label="Test"
                  type="number"
                  size="small"
                  autoComplete="off"
                  error={rowsPartitionsError}
                  defaultValue={rowsPartitionsPercentage.test}
                  onChange={handleRowsChange}
                />
              </Grid>
              <Grid item xs={12} sx={{ ml: 3 }}>
                <BooleanInput
                  name="shuffle"
                  value={shuffle}
                  label="Shuffle"
                  onChange={handleShuffleChange}
                  description="Determines whether the data will be shuffled when defining the sets or not. It must be true to shuffle the data, otherwise false."
                />
                <BooleanInput
                  name="stratify"
                  value={stratify}
                  label="Stratify"
                  onChange={handleStratifyChange}
                  description="Defines whether the data will be proportionally separated according to the distribution of classes in each set. Shuffle must be true to stratify the data."
                />
                <TextField
                  id="seed"
                  label="Seed"
                  value={seed}
                  onChange={handleSeedChange}
                  autoComplete="off"
                  type="number"
                  size="small"
                  helperText="Enter a seed value for reproducibility (optional)"
                />
              </Grid>
            </Grid>
          )}
          {rowsPartitionsError ? (
            <FormHelperText>{rowsPartitionsErrorText}</FormHelperText>
          ) : (
            <React.Fragment />
          )}
        </React.Fragment>
        <React.Fragment />
        <FormControlLabel
          value={SPLIT_TYPES.MANUAL}
          control={<Radio />}
          label="Use manual splitting by specifying the row indexes of each subset"
          sx={{ my: 1 }}
        />
        <React.Fragment>
          {splitType === SPLIT_TYPES.MANUAL && (
            <Grid container direction="row" spacing={4}>
              <Grid item xs={4}>
                <TextField
                  id="train"
                  label="Train"
                  autoComplete="off"
                  size="small"
                  error={rowsPartitionsError}
                  onChange={handleRowsChange}
                />
              </Grid>
              <Grid item xs={4}>
                <TextField
                  id="validation"
                  label="Validation"
                  autoComplete="off"
                  size="small"
                  error={rowsPartitionsError}
                  onChange={handleRowsChange}
                />
              </Grid>
              <Grid item xs={4}>
                <TextField
                  id="test"
                  label="Test"
                  autoComplete="off"
                  size="small"
                  error={rowsPartitionsError}
                  onChange={handleRowsChange}
                />
              </Grid>
            </Grid>
          )}
          {rowsPartitionsError ? (
            <FormHelperText>{rowsPartitionsErrorText}</FormHelperText>
          ) : (
            <React.Fragment />
          )}
        </React.Fragment>
        <React.Fragment />
      </RadioGroup>
    </React.Fragment>
  );
}

SplitDatasetRows.propTypes = {
  datasetInfo: PropTypes.shape({
    test_size: PropTypes.number,
    total_columns: PropTypes.number,
    total_rows: PropTypes.number,
    train_size: PropTypes.number,
    val_size: PropTypes.number,
  }),
  rowsPartitionsIndex: PropTypes.shape({
    train: PropTypes.arrayOf(PropTypes.number),
    validation: PropTypes.arrayOf(PropTypes.number),
    test: PropTypes.arrayOf(PropTypes.number),
  }),
  setRowsPartitionsIndex: PropTypes.func.isRequired,
  rowsPartitionsPercentage: PropTypes.shape({
    train: PropTypes.number,
    validation: PropTypes.number,
    test: PropTypes.number,
  }),
  setRowsPartitionsPercentage: PropTypes.func.isRequired,
  setSplitsReady: PropTypes.func.isRequired,
  splitType: PropTypes.string.isRequired,
  setSplitType: PropTypes.func.isRequired,
  SPLIT_TYPES: PropTypes.object.isRequired,
  shuffle: PropTypes.bool.isRequired,
  setShuffle: PropTypes.func.isRequired,
  stratify: PropTypes.bool.isRequired,
  setStratify: PropTypes.func.isRequired,
};
export default SplitDatasetRows;
