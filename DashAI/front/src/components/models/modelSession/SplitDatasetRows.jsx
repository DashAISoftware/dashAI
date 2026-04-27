import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { parseRangeToIndex } from "../../../utils/parseRange";
import {
  Grid,
  TextField,
  Typography,
  FormControlLabel,
  Radio,
  RadioGroup,
  FormHelperText,
  Button,
  Box,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import BooleanInput from "../../configurableObject/Inputs/BooleanInput";
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
  divisionType,
  setDivisionType,
  cvType,
  setCvType,
  numFolds,
  setNumFolds,
  numRepeats,
  setNumRepeats,
  groupColumn,
  setGroupColumn,
  outputColumnNames,
  taskName,
}) {
  const { t } = useTranslation(["experiments"]);

  // Determine which CV types are allowed based on task type
  const getAllowedCvTypes = () => {
    if (!taskName)
      return [
        "kfold",
        "stratifiedKfold",
        "repeatedKfold",
        "repeatedStratifiedKfold",
        "groupKfold",
        "stratifiedGroupKfold",
        "leaveOneOut",
      ];

    // For regression tasks: only allow non-stratified CV types
    if (taskName.toLowerCase().includes("regression")) {
      return [
        "kfold",
        "repeatedKfold",
        "groupKfold",
        "repeatedGroupKfold",
        "leaveOneOut",
      ];
    }

    // For classification tasks (tabular or text): allow all CV types
    if (taskName.toLowerCase().includes("classification")) {
      return [
        "kfold",
        "stratifiedKfold",
        "repeatedKfold",
        "repeatedStratifiedKfold",
        "groupKfold",
        "stratifiedGroupKfold",
        "leaveOneOut",
      ];
    }

    // Default: all CV types
    return [
      "kfold",
      "stratifiedKfold",
      "repeatedKfold",
      "repeatedStratifiedKfold",
      "groupKfold",
      "stratifiedGroupKfold",
      "leaveOneOut",
    ];
  };

  const allowedCvTypes = getAllowedCvTypes();

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

  // Cross-Validation handlers
  const handleCvTypeChange = (event) => {
    setCvType(event.target.value);
    if (
      event.target.value === "stratifiedKfold" ||
      event.target.value === "repeatedStratifiedKfold" ||
      event.target.value === "stratifiedGroupKfold"
    ) {
      setStratify(true);
    } else {
      setStratify(false);
    }
  };

  const handleGroupColumnChange = (event) => {
    setGroupColumn(event.target.value);
  };

  const handleNumFoldsChange = (event) => {
    const value =
      event.target.value === ""
        ? ""
        : Math.max(1, Math.min(Number(event.target.value), 20));
    setNumFolds(value);
  };

  const handleOnBlurNumFolds = (event) => {
    if (event.target.value < 2) {
      setNumFolds(2);
    }
  };

  const handleOnBlurSeed = (event) => {
    if (event.target.value === "") {
      setSeed(42);
    }
  };

  const handleNumRepeatsChange = (event) => {
    const value =
      event.target.value === ""
        ? ""
        : Math.max(1, Math.min(Number(event.target.value), 10));
    setNumRepeats(value);
  };

  const handleOnBlurNumRepeats = (event) => {
    if (event.target.value < 2) {
      setNumRepeats(2);
    }
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

  // Reset cvType if it's not allowed for the current task
  useEffect(() => {
    if (!allowedCvTypes.includes(cvType)) {
      setCvType(allowedCvTypes[0]);
    }
  }, [allowedCvTypes, cvType, setCvType]);

  return (
    <React.Fragment>
      {/* Division Type Selection */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12 }}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 2 }}>
            {t("experiments:label.selectDivisionType")}
          </Typography>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Box sx={{ display: "flex", gap: 2 }}>
            <Button
              variant={divisionType === "holdout" ? "contained" : "outlined"}
              onClick={() => setDivisionType("holdout")}
              sx={{ flex: 1 }}
            >
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <Typography variant="subtitle2">
                  {t("experiments:label.holdout")}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ fontSize: "0.75rem", mt: 0.5 }}
                >
                  {t("experiments:label.holdoutDescription")}
                </Typography>
              </Box>
            </Button>
            <Button
              variant={
                divisionType === "crossValidation" ? "contained" : "outlined"
              }
              onClick={() => setDivisionType("crossValidation")}
              sx={{ flex: 1 }}
            >
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <Typography variant="subtitle2">
                  {t("experiments:label.crossValidation")}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ fontSize: "0.75rem", mt: 0.5 }}
                >
                  {t("experiments:label.crossValidationDescription")}
                </Typography>
              </Box>
            </Button>
          </Box>
        </Grid>
      </Grid>

      {/* Holdout Configuration */}
      {divisionType === "holdout" && (
        <Box sx={{ mb: 4 }}>
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
                      <FormHelperText error>
                        {randomSplitErrorText}
                      </FormHelperText>
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
                      <FormHelperText error>
                        {manualSplitErrorText}
                      </FormHelperText>
                    </Grid>
                  )}
                </Grid>
              </>
            )}
          </RadioGroup>
        </Box>
      )}

      {/* Cross-Validation Configuration */}
      {divisionType === "crossValidation" && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
            {t("experiments:label.crossValidation")}
          </Typography>

          {/* CV Type Selection */}
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>{t("experiments:label.cvType")}</InputLabel>
                <Select
                  value={cvType}
                  onChange={handleCvTypeChange}
                  label={t("experiments:label.cvType")}
                >
                  {allowedCvTypes.includes("kfold") && (
                    <MenuItem value="kfold">
                      {t("experiments:label.kfold")}
                    </MenuItem>
                  )}
                  {allowedCvTypes.includes("stratifiedKfold") && (
                    <MenuItem value="stratifiedKfold">
                      {t("experiments:label.stratifiedKfold")}
                    </MenuItem>
                  )}
                  {allowedCvTypes.includes("repeatedKfold") && (
                    <MenuItem value="repeatedKfold">
                      {t("experiments:label.repeatedKfold")}
                    </MenuItem>
                  )}
                  {allowedCvTypes.includes("repeatedStratifiedKfold") && (
                    <MenuItem value="repeatedStratifiedKfold">
                      {t("experiments:label.repeatedStratifiedKfold")}
                    </MenuItem>
                  )}
                  {allowedCvTypes.includes("groupKfold") && (
                    <MenuItem value="groupKfold">
                      {t("experiments:label.groupKfold")}
                    </MenuItem>
                  )}
                  {allowedCvTypes.includes("stratifiedGroupKfold") && (
                    <MenuItem value="stratifiedGroupKfold">
                      {t("experiments:label.stratifiedGroupKfold")}
                    </MenuItem>
                  )}
                  {allowedCvTypes.includes("leaveOneOut") && (
                    <MenuItem value="leaveOneOut">
                      {t("experiments:label.leaveOneOut")}
                    </MenuItem>
                  )}
                </Select>
              </FormControl>
            </Grid>

            {/* Group Column - only for GroupKFold or StratifiedGroupKFold */}
            {(cvType === "groupKfold" || cvType === "stratifiedGroupKfold") && (
              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>{t("experiments:label.groupColumn")}</InputLabel>
                  <Select
                    value={groupColumn}
                    onChange={handleGroupColumnChange}
                    label={t("experiments:label.groupColumn")}
                  >
                    {datasetInfo.column_names &&
                      datasetInfo.column_names
                        .filter((column) => !outputColumnNames.includes(column))
                        .map((column) => (
                          <MenuItem key={column} value={column}>
                            {column}
                          </MenuItem>
                        ))}
                  </Select>
                </FormControl>
              </Grid>
            )}

            {/* Number of Folds - shown for all except LeaveOneOut */}
            {cvType !== "leaveOneOut" && (
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  id="numFolds"
                  label={t("experiments:label.numFolds")}
                  type="number"
                  value={numFolds}
                  onChange={handleNumFoldsChange}
                  onBlur={handleOnBlurNumFolds}
                  inputProps={{ min: 2, max: 10 }}
                  helperText="Mínimo 2, máximo 10"
                />
              </Grid>
            )}

            {/* Number of Repeats - only for RepeatedKFold */}
            {(cvType === "repeatedKfold" ||
              cvType === "repeatedStratifiedKfold") && (
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  id="numRepeats"
                  label={t("experiments:label.numRepeats")}
                  type="number"
                  value={numRepeats}
                  onChange={handleNumRepeatsChange}
                  onBlur={handleOnBlurNumRepeats}
                  inputProps={{ min: 2, max: 10 }}
                  helperText="Mínimo 2, máximo 10"
                />
              </Grid>
            )}

            {/* Shuffle option */}
            {cvType !== "leaveOneOut" &&
              cvType !== "repeatedKfold" &&
              cvType !== "repeatedStratifiedKfold" && (
                <Grid size={{ xs: 12 }}>
                  <BooleanInput
                    name="shuffle"
                    value={shuffle}
                    label={t("experiments:label.shuffle")}
                    onChange={handleShuffleChange}
                    description="Mezclar los datos antes de dividir en pliegues"
                  />
                </Grid>
              )}

            {/* Seed for reproducibility */}
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                id="seed"
                label={t("experiments:label.seed")}
                type="number"
                value={seed}
                onChange={handleSeedChange}
                onBlur={handleOnBlurSeed}
                helperText={t("experiments:label.enterSeedValue")}
              />
            </Grid>

            {/* Summary of configuration */}
            <Grid size={{ xs: 12 }}>
              <Box
                sx={{
                  p: 2,
                  backgroundColor: "#0000007a",
                  borderRadius: 1,
                  mt: 2,
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Configuración Actual:
                </Typography>
                <Typography variant="body2">
                  {cvType === "kfold" &&
                    `K-Fold con ${numFolds} pliegues${shuffle ? " (barajeado)" : ""}`}
                  {cvType === "stratifiedKfold" &&
                    `K-Fold Estratificado con ${numFolds} pliegues${shuffle ? " (barajeado)" : ""}`}
                  {cvType === "repeatedKfold" &&
                    `K-Fold Repetido: ${numFolds} pliegues × ${numRepeats} repeticiones`}
                  {cvType === "repeatedStratifiedKfold" &&
                    `K-Fold Estratificado Repetido: ${numFolds} pliegues × ${numRepeats} repeticiones`}
                  {cvType === "groupKfold" &&
                    `Group K-Fold con ${numFolds} pliegues, usando la columna de grupos "${groupColumn}"${shuffle ? " (barajeado)" : ""}`}
                  {cvType === "stratifiedGroupKfold" &&
                    `Group K-Fold Estratificado con ${numFolds} pliegues, usando la columna de grupos "${groupColumn}"${shuffle ? " (barajeado)" : ""}`}
                  {cvType === "leaveOneOut" &&
                    `Leave-One-Out (n-1 splits, donde n es el tamaño del dataset)`}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Paper>
      )}
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
  divisionType: PropTypes.string.isRequired,
  setDivisionType: PropTypes.func.isRequired,
  cvType: PropTypes.string.isRequired,
  setCvType: PropTypes.func.isRequired,
  numFolds: PropTypes.number.isRequired,
  setNumFolds: PropTypes.func.isRequired,
  numRepeats: PropTypes.number.isRequired,
  setNumRepeats: PropTypes.func.isRequired,
  groupColumn: PropTypes.string,
  setGroupColumn: PropTypes.func.isRequired,
  outputColumnNames: PropTypes.arrayOf(PropTypes.string),
  taskName: PropTypes.string,
};

export default SplitDatasetRows;
