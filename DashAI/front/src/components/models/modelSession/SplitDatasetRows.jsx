import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { parseRangeToIndex } from "../../../utils/parseRange";
import {
  Box,
  FormHelperText,
  Grid,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import BooleanInput from "../../configurableObject/Inputs/BooleanInput";
import FormSchemaFieldCard from "../../shared/FormSchemaFieldCard";
import { useTranslation } from "react-i18next";

/**
 * Splits card shell — same Paper/header visual as FormSchemaFieldCard but WITHOUT
 * the label-hiding CSS so Train / Validation / Test TextField labels stay visible.
 */
function SplitsCard({ label, description, errorMessage, children }) {
  return (
    <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden" }}>
      <Box
        sx={{
          px: 2,
          py: 0.75,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography
          variant="body2"
          fontWeight={600}
          color={errorMessage ? "error.main" : "text.primary"}
        >
          {label}
        </Typography>
      </Box>
      <Box sx={{ px: 2, pt: 0.5, pb: description || errorMessage ? 0.5 : 1 }}>
        {children}
      </Box>
      {(description || errorMessage) && (
        <Box sx={{ px: 2, pb: 0.5 }}>
          <Typography
            component="span"
            variant="caption"
            color={errorMessage ? "error.main" : "text.disabled"}
            sx={{ display: "block", lineHeight: 1.5 }}
          >
            {errorMessage ?? description}
          </Typography>
        </Box>
      )}
    </Paper>
  );
}

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
  evaluationStrategy,
  setEvaluationStrategy,
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
  const { t } = useTranslation(["experiments", "common"]);

  // Determine which CV types are allowed based on task type
  const getAllowedCvTypes = () => {
    if (!taskName)
      return [
        "KFold",
        "StratifiedKFold",
        "RepeatedKFold",
        "RepeatedStratifiedKFold",
        "GroupKFold",
        "StratifiedGroupKFold",
        "LeaveOneOut",
      ];

    // For regression tasks: only allow non-stratified CV types
    if (taskName.toLowerCase().includes("regression")) {
      return [
        "KFold",
        "RepeatedKFold",
        "GroupKFold",
        "RepeatedGroupKFold",
        "LeaveOneOut",
      ];
    }

    // For classification tasks (tabular or text): allow all CV types
    if (taskName.toLowerCase().includes("classification")) {
      return [
        "KFold",
        "StratifiedKFold",
        "RepeatedKFold",
        "RepeatedStratifiedKFold",
        "GroupKFold",
        "StratifiedGroupKFold",
        "LeaveOneOut",
      ];
    }

    // Default: all CV types
    return [
      "KFold",
      "StratifiedKFold",
      "RepeatedKFold",
      "RepeatedStratifiedKFold",
      "GroupKFold",
      "StratifiedGroupKFold",
      "LeaveOneOut",
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

  const checkSplit = (train, validation, test) =>
    Math.abs(train + validation + test - 1) < 0.0001;

  const [randomSplitError, setRandomSplitError] = useState(false);
  const [randomSplitErrorText, setRandomSplitErrorText] = useState("");
  const [manualSplitError, setManualSplitError] = useState(false);
  const [manualSplitErrorText, setManualSplitErrorText] = useState("");

  const handleSplitTypeChange = (_e, newType) => {
    if (!newType) return;
    setSplitType(newType);

    if (newType === SPLIT_TYPES.PREDEFINED) {
      setSplitsReady(true);
    }
    if (newType === SPLIT_TYPES.RANDOM) {
      const newSplit = { train: 0.6, test: 0.2, validation: 0.2 };
      setRowsPartitionsPercentage(newSplit);
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
      setManualSplitErrorText(
        t("experiments:error.trainSplitMustHaveAtLeastOneRow"),
      );
      setManualSplitError(true);
    }
  };

  const handleRowsChange = (event) => {
    const value = event.target.value;
    const id = event.target.id;

    if (splitType === SPLIT_TYPES.MANUAL) {
      try {
        const rowsIndex = parseRangeToIndex(value, totalRows);
        const updatedIndex = { ...rowsPartitionsIndex, [id]: rowsIndex };
        setRowsPartitionsIndex(updatedIndex);
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
      const numValue = parseFloat(value) || 0;
      const newSplit = { ...rowsPartitionsPercentage, [id]: numValue };
      setRowsPartitionsPercentage(newSplit);
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
    if (!value) setStratify(false);
  };

  const handleStratifyChange = (value) => {
    if (shuffle) setStratify(value);
    else setStratify(false);
  };

  const handleSeedChange = (event) => {
    const value = event.target.value === "" ? "" : Number(event.target.value);
    setSeed(value);
  };

  // Cross-Validation handlers
  const handleCvTypeChange = (event) => {
    setCvType(event.target.value);
    if (
      event.target.value === "StratifiedKFold" ||
      event.target.value === "RepeatedStratifiedKFold" ||
      event.target.value === "StratifiedGroupKFold"
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

  // Check if current cvType is a repeated CV type
  const isRepeatedCvType = () => {
    return cvType?.includes("Repeated");
  };

  // Check if current cvType is a grouping CV type
  const isGroupingCvType = () => {
    return cvType?.includes("Group");
  };

  // Check if LeaveOneOut
  const isLeaveOneOut = () => {
    return cvType === "LeaveOneOut";
  };

  useEffect(() => {
    if (hasPredefinedSplits) {
      setSplitType(SPLIT_TYPES.PREDEFINED);
    } else {
      setSplitType(SPLIT_TYPES.RANDOM);
    }
  }, [hasPredefinedSplits]);

  useEffect(() => {
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
    } else if (evaluationStrategy === "CrossValidationEvaluationStrategy") {
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
    evaluationStrategy,
  ]);

  const splitOptions = [
    {
      value: SPLIT_TYPES.PREDEFINED,
      label: t("experiments:label.predefined"),
      disabled: !hasPredefinedSplits,
    },
    { value: SPLIT_TYPES.RANDOM, label: t("experiments:label.random") },
    { value: SPLIT_TYPES.MANUAL, label: t("experiments:label.manual") },
  ];

  const splitFields = [
    { id: "train", label: t("common:train") },
    { id: "validation", label: t("common:validation") },
    { id: "test", label: t("common:test") },
  ];

  // Reset cvType if it's not allowed for the current task
  useEffect(() => {
    if (!allowedCvTypes.includes(cvType)) {
      setCvType(allowedCvTypes[0]);
    }
  }, [allowedCvTypes, cvType, setCvType]);

  console.log("rendering evaluation strategy:", evaluationStrategy);
  return (
    <Stack spacing={1} data-tour="exp-dataset-splits">
      {/* Evaluation Strategy Selector */}
      <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden" }}>
        <Box
          sx={{
            px: 2,
            py: 0.75,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="body2" fontWeight={600}>
            {t("experiments:label.evaluationStrategy")}
          </Typography>
        </Box>
        <Box sx={{ px: 2, pt: 0.5, pb: 1 }}>
          <ToggleButtonGroup
            value={evaluationStrategy}
            exclusive={true}
            onChange={(_, value) => {
              console.log("onChange fired, value:", value);
              value && setEvaluationStrategy(value);
            }}
            fullWidth
            size="small"
          >
            <ToggleButton
              value="HoldoutEvaluationStrategy"
              sx={{ textTransform: "none", fontSize: "0.8rem" }}
            >
              Holdout
            </ToggleButton>
            <ToggleButton
              value="CrossValidationEvaluationStrategy"
              sx={{ textTransform: "none", fontSize: "0.8rem" }}
            >
              Cross-Validation
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Paper>

      {/* HOLDOUT SECTION */}
      {evaluationStrategy === "HoldoutEvaluationStrategy" && (
        <>
          {/* Split type selector */}
          <Paper
            variant="outlined"
            sx={{ borderRadius: 2, overflow: "hidden" }}
          >
            <Box
              sx={{
                px: 2,
                py: 0.75,
                borderBottom: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="body2" fontWeight={600}>
                {t("experiments:label.splitType")}
              </Typography>
            </Box>
            <Box sx={{ px: 2, pt: 0.5, pb: 1 }}>
              <ToggleButtonGroup
                value={splitType}
                exclusive
                onChange={handleSplitTypeChange}
                fullWidth
                size="small"
              >
                {splitOptions.map((opt) => (
                  <ToggleButton
                    key={opt.value}
                    value={opt.value}
                    disabled={opt.disabled}
                    sx={{ textTransform: "none", fontSize: "0.8rem" }}
                  >
                    {opt.label}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mb: 0.75 }}
              >
                {t("experiments:label.selectHowToDivideDataset")}
              </Typography>
            </Box>
          </Paper>

          {/* Predefined */}
          {splitType === SPLIT_TYPES.PREDEFINED && (
            <SplitsCard
              label={t("experiments:label.splits")}
              description={t("experiments:label.splitsDescription")}
            >
              <Grid container spacing={1}>
                {[
                  { id: "train", value: trainDatasetPercentage },
                  { id: "validation", value: validationDatasetPercentage },
                  { id: "test", value: testDatasetPercentage },
                ].map(({ id, value }) => (
                  <Grid key={id} size={{ xs: 4 }}>
                    <TextField
                      label={t(`common:${id}`)}
                      value={value}
                      type="number"
                      size="small"
                      fullWidth
                      disabled
                      slotProps={{ inputLabel: { shrink: true } }}
                      sx={{
                        "& .MuiInputBase-input.Mui-disabled": {
                          WebkitTextFillColor: "#999",
                        },
                        "& .MuiInputLabel-root.Mui-disabled": { color: "#bbb" },
                      }}
                    />
                  </Grid>
                ))}
              </Grid>
            </SplitsCard>
          )}

          {/* Random */}
          {splitType === SPLIT_TYPES.RANDOM && (
            <>
              <SplitsCard
                label={t("experiments:label.splits")}
                description={t("experiments:label.splitsDescription")}
                errorMessage={
                  randomSplitError ? randomSplitErrorText : undefined
                }
              >
                <Grid container spacing={1}>
                  {splitFields.map(({ id, label }) => (
                    <Grid key={id} size={{ xs: 4 }}>
                      <TextField
                        id={id}
                        label={label}
                        value={rowsPartitionsPercentage[id]}
                        type="number"
                        size="small"
                        fullWidth
                        error={randomSplitError}
                        onChange={handleRowsChange}
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                    </Grid>
                  ))}
                </Grid>
              </SplitsCard>

              <FormSchemaFieldCard
                label={t("experiments:label.shuffle")}
                description={t("experiments:label.shuffleDescription")}
              >
                <BooleanInput
                  name="shuffle"
                  value={shuffle}
                  label={t("experiments:label.shuffle")}
                  onChange={handleShuffleChange}
                  description={t("experiments:label.shuffleDescription")}
                />
              </FormSchemaFieldCard>

              <FormSchemaFieldCard
                label={t("experiments:label.stratify")}
                description={
                  !shuffle
                    ? t("experiments:label.stratifyRequiresShuffle")
                    : t("experiments:label.stratifyDescription")
                }
              >
                <BooleanInput
                  name="stratify"
                  value={stratify}
                  label={t("experiments:label.stratify")}
                  onChange={handleStratifyChange}
                  description={t("experiments:label.stratifyDescription")}
                />
              </FormSchemaFieldCard>

              <FormSchemaFieldCard
                label={t("experiments:label.seed")}
                description={t("experiments:label.enterSeedValue")}
              >
                <TextField
                  id="seed"
                  label={t("experiments:label.seed")}
                  value={seed}
                  onChange={handleSeedChange}
                  type="number"
                  size="small"
                  fullWidth
                />
              </FormSchemaFieldCard>
            </>
          )}

          {/* Manual */}
          {splitType === SPLIT_TYPES.MANUAL && (
            <SplitsCard
              label={t("experiments:label.rowIndexes")}
              description={t("experiments:label.rowIndexesDescription")}
              errorMessage={manualSplitError ? manualSplitErrorText : undefined}
            >
              <Grid container spacing={1}>
                {splitFields.map(({ id, label }) => (
                  <Grid key={id} size={{ xs: 4 }}>
                    <TextField
                      id={id}
                      label={label}
                      size="small"
                      fullWidth
                      error={manualSplitError}
                      onChange={handleRowsChange}
                      slotProps={{ inputLabel: { shrink: true } }}
                    />
                  </Grid>
                ))}
              </Grid>
            </SplitsCard>
          )}
        </>
      )}

      {/* CROSS-VALIDATION SECTION */}
      {evaluationStrategy === "CrossValidationEvaluationStrategy" && (
        <>
          {/* CV Type Selector */}
          <FormControl fullWidth>
            <InputLabel>{t("experiments:label.cvType")}</InputLabel>
            <Select
              value={cvType}
              onChange={handleCvTypeChange}
              label={t("experiments:label.cvType")}
            >
              {allowedCvTypes.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Number of Folds - not for LeaveOneOut */}
          {!isLeaveOneOut() && (
            <FormSchemaFieldCard
              label={t("experiments:label.numFolds")}
              description={t("experiments:label.numFoldsDescription")}
            >
              <TextField
                id="numFolds"
                label={t("experiments:label.numFolds")}
                value={numFolds}
                onChange={handleNumFoldsChange}
                onBlur={handleOnBlurNumFolds}
                type="number"
                size="small"
                fullWidth
                inputProps={{ min: 2, max: 20 }}
              />
            </FormSchemaFieldCard>
          )}

          {/* Number of Repeats - only for Repeated CV types */}
          {isRepeatedCvType() && (
            <FormSchemaFieldCard
              label={t("experiments:label.numRepeats")}
              description={t("experiments:label.numRepeatsDescription")}
            >
              <TextField
                id="numRepeats"
                label={t("experiments:label.numRepeats")}
                value={numRepeats}
                onChange={handleNumRepeatsChange}
                onBlur={handleOnBlurNumRepeats}
                type="number"
                size="small"
                fullWidth
                inputProps={{ min: 2, max: 10 }}
              />
            </FormSchemaFieldCard>
          )}

          {/* Group Column - only for GroupKFold types */}
          {isGroupingCvType() && (
            <FormControl fullWidth>
              <InputLabel>{t("experiments:label.groupColumn")}</InputLabel>
              <Select
                value={groupColumn || ""}
                onChange={handleGroupColumnChange}
                label={t("experiments:label.groupColumn")}
              >
                {outputColumnNames?.map((col) => (
                  <MenuItem key={col} value={col}>
                    {col}
                  </MenuItem>
                )) || []}
              </Select>
            </FormControl>
          )}

          {/* Shuffle - only if NOT a repeated CV type */}
          {!isRepeatedCvType() && (
            <FormSchemaFieldCard
              label={t("experiments:label.shuffle")}
              description={t("experiments:label.shuffleDescription")}
            >
              <BooleanInput
                name="shuffle"
                value={shuffle}
                label={t("experiments:label.shuffle")}
                onChange={handleShuffleChange}
                description={t("experiments:label.shuffleDescription")}
              />
            </FormSchemaFieldCard>
          )}

          {/* Seed */}
          <FormSchemaFieldCard
            label={t("experiments:label.seed")}
            description={t("experiments:label.enterSeedValue")}
          >
            <TextField
              id="seed"
              label={t("experiments:label.seed")}
              value={seed}
              onChange={handleSeedChange}
              onBlur={handleOnBlurSeed}
              type="number"
              size="small"
              fullWidth
            />
          </FormSchemaFieldCard>
        </>
      )}
    </Stack>
  );
}

SplitDatasetRows.propTypes = {
  datasetInfo: PropTypes.object.isRequired,
  rowsPartitionsIndex: PropTypes.object.isRequired,
  setRowsPartitionsIndex: PropTypes.func.isRequired,
  rowsPartitionsPercentage: PropTypes.object.isRequired,
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
  evaluationStrategy: PropTypes.string.isRequired,
  setEvaluationStrategy: PropTypes.func.isRequired,
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
