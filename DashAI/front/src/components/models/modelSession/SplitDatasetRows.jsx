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
import { SplitscreenOutlined } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { getComponents } from "../../../api/component";

/**
 * Splits card shell — same Paper/header visual as FormSchemaFieldCard but WITHOUT
 * the label-hiding CSS so Train / Validation / Test TextField labels stay visible.
 */
function SplitsCard({ label, description, errorMessage, children, warning }) {
  return (
    <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden" }}>
      <Box
        sx={{
          px: 4,
          py: 3,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography
          variant="body2"
          fontWeight={600}
          color={
            errorMessage
              ? "error.main"
              : warning
                ? "warning.main"
                : "text.primary"
          }
        >
          {label}
        </Typography>
      </Box>
      <Box sx={{ px: 8, pt: 2, pb: description || errorMessage ? 2 : 4 }}>
        {children}
      </Box>
      {(description || errorMessage || warning) && (
        <Box sx={{ px: 8, pb: 2 }}>
          <Typography
            component="span"
            variant="caption"
            color={
              errorMessage
                ? "error.main"
                : warning
                  ? "warning.main"
                  : "text.disabled"
            }
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
  inputColumnNames,
  taskName,
}) {
  const { t } = useTranslation(["experiments", "common"]);
  const { enqueueSnackbar } = useSnackbar();

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

  const [cvFoldError, setCvFoldError] = useState(false);
  const [cvFoldErrorText, setCvFoldErrorText] = useState("");
  const [cvRepeatError, setCvRepeatError] = useState(false);
  const [cvRepeatErrorText, setCvRepeatErrorText] = useState("");
  const [groupColumnError, setGroupColumnError] = useState(true);
  const [allowedCvTypes, setAllowedCvTypes] = useState([]);

  // Update allowed CV types when task changes
  useEffect(() => {
    const getSplittersForTask = async () => {
      try {
        const response = await getComponents({
          selectTypes: ["Splitter"],
          relatedComponent: taskName,
        });
        setAllowedCvTypes(response);
      } catch (error) {
        console.error("Error fetching splitters:", error);
        enqueueSnackbar(t("models:error.fetchingStatisticalTests"), {
          variant: "error",
        });
      }
    };

    getSplittersForTask();
  }, [taskName]);

  // Set default CV type when allowedCvTypes changes
  useEffect(() => {
    setCvType(allowedCvTypes.length > 0 ? allowedCvTypes[0] : null);
  }, [allowedCvTypes]);

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

  const handleGroupColumnChange = (event) => {
    const value = event.target.value;
    setGroupColumn(value);
    if (value) {
      setGroupColumnError(false);
    } else {
      setGroupColumnError(true);
    }
  };

  const handleNumFoldsChange = (event) => {
    const value = event.target.value === "" ? "" : Number(event.target.value);
    setNumFolds(value);
    if (value !== "" && value > 1 && value <= datasetInfo.total_rows) {
      setCvFoldError(false);
      setCvFoldErrorText("");
      return;
    }

    if (value === "") {
      setCvFoldErrorText(t("experiments:error.foldsMustBeAnInteger"));
    } else if (value <= 1) {
      setCvFoldErrorText(t("experiments:error.foldsMustBeGreaterThanOne"));
    } else if (value > datasetInfo.total_rows) {
      setCvFoldErrorText(
        t("experiments:error.foldsMustBeLessThanDatasetSize", {
          datasetSize: datasetInfo.total_rows,
        }),
      );
    }
    setCvFoldError(true);
    return;
  };

  const handleOnBlurSeed = (event) => {
    if (event.target.value === "") {
      setSeed(42);
    }
  };

  const handleNumRepeatsChange = (event) => {
    const value = event.target.value === "" ? "" : Number(event.target.value);
    setNumRepeats(value);
    if (value !== "" && value > 1) {
      setCvRepeatError(false);
      setCvRepeatErrorText("");
      return;
    }
    if (value === "") {
      setCvRepeatErrorText(t("experiments:error.repeatsMustBeGreaterThanOne"));
    } else if (value <= 1) {
      setCvRepeatErrorText(t("experiments:error.repeatsMustBeGreaterThanOne"));
    }
    setCvRepeatError(true);
    return;
  };

  useEffect(() => {
    if (hasPredefinedSplits) {
      setSplitType(SPLIT_TYPES.PREDEFINED);
    } else {
      setSplitType(SPLIT_TYPES.RANDOM);
    }
  }, [hasPredefinedSplits]);

  useEffect(() => {
    if (evaluationStrategy === "HoldoutEvaluationStrategy") {
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
    } else if (evaluationStrategy === "CrossValidationEvaluationStrategy") {
      if (!cvFoldError && !cvRepeatError && !groupColumnError) {
        setSplitsReady(true);
      } else {
        setSplitsReady(false);
      }
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
    cvFoldError,
    cvRepeatError,
    groupColumnError,
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

  // Validate group column when grouping CV type is selected
  useEffect(() => {
    const isGrouping = cvType?.metadata?.hasGroups || false;
    if (isGrouping && !groupColumn) {
      setGroupColumnError(true);
    } else {
      setGroupColumnError(false);
    }
  }, [cvType, groupColumn, t]);

  return (
    <Stack spacing={4} data-tour="exp-dataset-splits">
      {/* Evaluation Strategy Selector */}
      <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden" }}>
        <Box
          sx={{
            px: 8,
            py: 3,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="body2" fontWeight={600}>
            {t("experiments:label.selectEvaluationStrategy")}
          </Typography>
        </Box>
        <Box sx={{ px: 8, pt: 2, pb: 4 }}>
          <ToggleButtonGroup
            value={evaluationStrategy}
            exclusive={true}
            onChange={(_, value) => {
              value && setEvaluationStrategy(value);
            }}
            fullWidth
            size="small"
          >
            <ToggleButton
              value="HoldoutEvaluationStrategy"
              sx={{ textTransform: "none", fontSize: "0.8rem" }}
            >
              {t("experiments:label.holdout")}
            </ToggleButton>
            <ToggleButton
              value="CrossValidationEvaluationStrategy"
              sx={{ textTransform: "none", fontSize: "0.8rem" }}
            >
              {t("experiments:label.crossValidation")}
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
                sx={{ display: "block", mb: 3 }}
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
              <Grid container spacing={2}>
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
                <Grid container spacing={4}>
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
                        slotProps={{
                          inputLabel: { shrink: true },
                          htmlInput: { step: 0.1 },
                        }}
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
              <Grid container spacing={2}>
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
          <SplitsCard label={t("experiments:label.cvType")}>
            <FormControl fullWidth size="small">
              <Select
                value={cvType}
                onChange={(e) => setCvType(e.target.value)}
              >
                {allowedCvTypes.map((type) => (
                  <MenuItem key={type.name} value={type}>
                    {type.display_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </SplitsCard>

          {/* Number of Folds */}
          {cvType?.metadata?.hasFolds && (
            <SplitsCard
              label={t("experiments:label.numFolds")}
              description={t("experiments:label.numFoldsDescription")}
              errorMessage={cvFoldError ? cvFoldErrorText : undefined}
            >
              <TextField
                id="numFolds"
                value={numFolds}
                onChange={handleNumFoldsChange}
                type="number"
                size="small"
                fullWidth
                error={cvFoldError}
                inputProps={{ min: 2, max: 20 }}
              />
            </SplitsCard>
          )}

          {/* Number of Repeats */}
          {cvType?.metadata?.hasRepeats && (
            <SplitsCard
              label={t("experiments:label.numRepeats")}
              description={t("experiments:label.numRepeatsDescription")}
              errorMessage={cvRepeatError ? cvRepeatErrorText : undefined}
            >
              <TextField
                id="numRepeats"
                value={numRepeats}
                onChange={handleNumRepeatsChange}
                type="number"
                size="small"
                fullWidth
                error={cvRepeatError}
                inputProps={{ min: 2, max: 10 }}
              />
            </SplitsCard>
          )}

          {/* Group Column */}
          {cvType?.metadata?.hasGroups && (
            <SplitsCard
              label={t("experiments:label.groupColumn")}
              description={t("experiments:label.groupColumnDescription")}
              warning={groupColumnError && !groupColumn ? true : false}
            >
              <FormControl fullWidth size="small">
                <Select
                  value={groupColumn || ""}
                  onChange={handleGroupColumnChange}
                  error={groupColumnError && !groupColumn}
                  displayEmpty
                >
                  <MenuItem value="" disabled>
                    <em>{t("experiments:label.selectAColumn")}</em>
                  </MenuItem>
                  {inputColumnNames?.map((col) => (
                    <MenuItem key={col} value={col}>
                      {col}
                    </MenuItem>
                  )) || []}
                </Select>
              </FormControl>
            </SplitsCard>
          )}

          {/* Shuffle */}
          {cvType?.metadata?.hasShuffle && (
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
  inputColumnNames: PropTypes.arrayOf(PropTypes.string),
  taskName: PropTypes.string,
};

export default SplitDatasetRows;
