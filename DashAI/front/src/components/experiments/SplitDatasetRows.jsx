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
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation(["experiments"]);

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
    const sum = train + validation + test;
    const tolerance = 0.0001; // Allow small floating point errors
    return Math.abs(sum - 1) < tolerance;
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
  const [randomSplitError, setRandomSplitError] = useState(false);
  const [randomSplitErrorText, setRandomSplitErrorText] = useState("");
  const [manualSplitError, setManualSplitError] = useState(false);
  const [manualSplitErrorText, setManualSplitErrorText] = useState("");

  const handleSplitTypeChange = (event) => {
    const newType = event.target.value;
    setSplitType(newType);

    if (newType === SPLIT_TYPES.PREDEFINED) {
      setSplitsReady(true);
    }
    if (newType === SPLIT_TYPES.RANDOM) {
      const newSplit = { train: 0.6, test: 0.2, validation: 0.2 };
      setRowsPartitionsPercentage(newSplit);

      // Validate the random split
      const hasZero = newSplit.train === 0;
      const sumsToOne = checkSplit(
        newSplit.train,
        newSplit.validation,
        newSplit.test,
      );

      if (hasZero) {
        setRandomSplitErrorText(
          t("experiments:error.trainSplitMustBeGreaterThanZero"),
        );
        setRandomSplitError(true);
      } else if (!sumsToOne) {
        setRandomSplitErrorText(t("experiments:error.splitsMustSumToOne"));
        setRandomSplitError(true);
      } else {
        setRandomSplitError(false);
      }
    }
    if (newType === SPLIT_TYPES.MANUAL) {
      const newIndex = { train: [], test: [], validation: [] };
      setRowsPartitionsIndex(newIndex);

      // Validate the manual split
      if (newIndex.train.length === 0) {
        setManualSplitErrorText(
          t("experiments:error.trainSplitMustHaveAtLeastOneRow"),
        );
        setManualSplitError(true);
      } else {
        setManualSplitError(false);
      }
    }
  };

  const handleRowsChange = (event) => {
    const value = event.target.value;
    const id = event.target.id;

    if (splitType === SPLIT_TYPES.MANUAL) {
      try {
        const rowsIndex = parseRangeToIndex(value, totalRows);
        let updatedIndex = { ...rowsPartitionsIndex };

        switch (id) {
          case "train":
            updatedIndex.train = rowsIndex;
            break;
          case "validation":
            updatedIndex.validation = rowsIndex;
            break;
          case "test":
            updatedIndex.test = rowsIndex;
            break;
        }

        setRowsPartitionsIndex(updatedIndex);

        // Validate after update
        if (updatedIndex.train.length === 0) {
          setManualSplitErrorText(
            t("experiments:error.trainSplitMustHaveAtLeastOneRow"),
          );
          setManualSplitError(true);
        } else {
          setManualSplitError(false);
        }
      } catch (error) {
        setManualSplitErrorText(error.message);
        setManualSplitError(true);
      }
    } else {
      let newSplit = { ...rowsPartitionsPercentage };
      const numValue = parseFloat(value) || 0;

      switch (id) {
        case "train":
          newSplit = { ...newSplit, train: numValue };
          break;
        case "validation":
          newSplit = { ...newSplit, validation: numValue };
          break;
        case "test":
          newSplit = { ...newSplit, test: numValue };
          break;
      }

      setRowsPartitionsPercentage(newSplit);

      // Check if any value is 0 or if sum is not 1
      const hasZero = newSplit.train === 0;
      const sumsToOne = checkSplit(
        newSplit.train,
        newSplit.validation,
        newSplit.test,
      );

      if (hasZero) {
        setRandomSplitErrorText(
          t("experiments:error.trainSplitMustBeGreaterThanZero"),
        );
        setRandomSplitError(true);
      } else if (!sumsToOne) {
        setRandomSplitErrorText(t("experiments:error.splitsMustSumToOne"));
        setRandomSplitError(true);
      } else {
        setRandomSplitError(false);
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
    const value = event.target.value === "" ? "" : Number(event.target.value);
    setSeed(value);
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
      !manualSplitError &&
      rowsPartitionsIndex.train.length >= 1
    ) {
      setSplitsReady(true);
    } else if (
      splitType === SPLIT_TYPES.RANDOM &&
      !randomSplitError &&
      rowsPartitionsPercentage.train > 0
    ) {
      setSplitsReady(true);
    } else {
      setSplitsReady(false);
    }
  }, [
    rowsPartitionsIndex,
    rowsPartitionsPercentage,
    randomSplitError,
    manualSplitError,
    splitType,
  ]);

  return (
    <React.Fragment>
      <Grid container spacing={1}>
        <Grid size={{ xs: 12 }}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 2 }}>
            {t("experiments:label.selectHowToDivideDataset")}
          </Typography>
        </Grid>
      </Grid>
      <RadioGroup
        data-tour="exp-dataset-splits"
        value={splitType}
        onChange={handleSplitTypeChange}
        name="radio-buttons-group"
      >
        <FormControlLabel
          value={SPLIT_TYPES.PREDEFINED}
          control={<Radio />}
          label={
            hasPredefinedSplits
              ? t("experiments:label.usePredefinedSplitsFromDataset")
              : t(
                  "experiments:label.usePredefinedSplitsFromDatasetNotAvailable",
                )
          }
          sx={{ my: 1 }}
          disabled={!hasPredefinedSplits}
        />
        {splitType === SPLIT_TYPES.PREDEFINED && (
          <Grid container direction="row" spacing={4}>
            <Grid size={{ xs: 4 }}>
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
            <Grid size={{ xs: 4 }}>
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
            <Grid size={{ xs: 4 }}>
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
          label={t("experiments:label.useRandomRowsBySpecifyingPortion")}
          sx={{ my: 1 }}
        />
        {splitType === SPLIT_TYPES.RANDOM && (
          <>
            <Grid container direction="row" spacing={4}>
              <Grid size={{ xs: 4 }}>
                <TextField
                  id="train"
                  label="Train"
                  autoComplete="off"
                  type="number"
                  size="small"
                  error={randomSplitError}
                  value={rowsPartitionsPercentage.train}
                  onChange={handleRowsChange}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid size={{ xs: 4 }}>
                <TextField
                  id="validation"
                  label="Validation"
                  autoComplete="off"
                  type="number"
                  size="small"
                  error={randomSplitError}
                  value={rowsPartitionsPercentage.validation}
                  onChange={handleRowsChange}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid size={{ xs: 4 }}>
                <TextField
                  id="test"
                  label="Test"
                  type="number"
                  size="small"
                  autoComplete="off"
                  error={randomSplitError}
                  value={rowsPartitionsPercentage.test}
                  onChange={handleRowsChange}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              {randomSplitError && (
                <Grid size={{ xs: 12 }}>
                  <FormHelperText error>{randomSplitErrorText}</FormHelperText>
                </Grid>
              )}
              <Grid size={{ xs: 12 }} sx={{ ml: 3 }}>
                <BooleanInput
                  name="shuffle"
                  value={shuffle}
                  label={t("experiments:label.shuffle")}
                  onChange={handleShuffleChange}
                  description={t("experiments:label.shuffleDescription")}
                />
                <BooleanInput
                  name="stratify"
                  value={stratify}
                  label={t("experiments:label.stratify")}
                  onChange={handleStratifyChange}
                  description={t("experiments:label.stratifyDescription")}
                />
                <TextField
                  id="seed"
                  label={t("experiments:label.seed")}
                  value={seed}
                  onChange={handleSeedChange}
                  autoComplete="off"
                  type="number"
                  size="small"
                  helperText={t("experiments:label.enterSeedValue")}
                />
              </Grid>
            </Grid>
          </>
        )}
        <FormControlLabel
          value={SPLIT_TYPES.MANUAL}
          control={<Radio />}
          label={t(
            "experiments:label.useManualSplittingBySpecifyingRowIndexes",
          )}
          sx={{ my: 1 }}
        />
        {splitType === SPLIT_TYPES.MANUAL && (
          <>
            <Grid container direction="row" spacing={4}>
              <Grid size={{ xs: 4 }}>
                <TextField
                  id="train"
                  label={t("common:train")}
                  autoComplete="off"
                  size="small"
                  error={manualSplitError}
                  onChange={handleRowsChange}
                />
              </Grid>
              <Grid size={{ xs: 4 }}>
                <TextField
                  id="validation"
                  label={t("common:validation")}
                  autoComplete="off"
                  size="small"
                  error={manualSplitError}
                  onChange={handleRowsChange}
                />
              </Grid>
              <Grid size={{ xs: 4 }}>
                <TextField
                  id="test"
                  label={t("common:test")}
                  autoComplete="off"
                  size="small"
                  error={manualSplitError}
                  onChange={handleRowsChange}
                />
              </Grid>
              {manualSplitError && (
                <Grid size={{ xs: 12 }}>
                  <FormHelperText error>{manualSplitErrorText}</FormHelperText>
                </Grid>
              )}
            </Grid>
          </>
        )}
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
  seed: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  setSeed: PropTypes.func.isRequired,
};

export default SplitDatasetRows;
