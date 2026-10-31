import React, { useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { parseRangeToIndex } from "../../../utils/parseRange";
import {
  Alert,
  FormHelperText,
  Grid,
  Paper,
  Box,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  Select,
  MenuItem,
  FormControl,
} from "@mui/material";
import FormSchema from "../../shared/FormSchema";
import FormSchemaLayout from "../../shared/FormSchemaLayout";
import SplitsCard from "./SplitsCard";
import SplitPreview from "./SplitPreview";
import {
  defaultSplitterOf,
  findStrategy,
  splittersOf,
  STRATEGY_KINDS,
  strategyKindOf,
} from "../../../utils/splitsPayload";
import useSplitPreview from "../../../hooks/useSplitPreview";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import { getComponents } from "../../../api/component";

function SplitDatasetRows({
  datasetId,
  datasetInfo,
  rowsPartitionsIndex,
  setRowsPartitionsIndex,
  setSplitsReady,
  setSplitPartitions,
  splitType,
  setSplitType,
  SPLIT_TYPES,
  splitterParams,
  setSplitterParams,
  paramsError,
  setParamsError,
  evaluationStrategy,
  setEvaluationStrategy,
  splitter,
  setSplitter,
  strategyKind,
  setStrategyKind,
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

  const splitterName =
    strategyKind && strategyKind !== STRATEGY_KINDS.FULL
      ? (splitter?.name ?? null)
      : null;
  const isHoldout = strategyKind === STRATEGY_KINDS.HOLDOUT;
  // Which splitter the parameters in splitterParams were given for: its form
  // or its schema defaults. Until they are this splitter's, they may still be
  // the previous one's, and nothing is previewed or created with them.
  const [paramsOwner, setParamsOwnerState] = useState(null);
  // The same, for the seed that resolves between renders.
  const paramsOwnerRef = useRef(null);
  const setParamsOwner = (name) => {
    paramsOwnerRef.current = name;
    setParamsOwnerState(name);
  };
  const paramsOwned = Boolean(splitterName) && paramsOwner === splitterName;
  const submitSplitterParams = (values) => {
    setParamsOwner(splitterName);
    setSplitterParams(values);
  };
  const isIndexMode =
    isHoldout &&
    (splitType === SPLIT_TYPES.MANUAL || splitType === SPLIT_TYPES.PREDEFINED);
  // group_column is rendered by hand because its options are the dataset's own
  // columns, so the generated form never validates it.
  // Memoized because the generated form memoizes its field list on this array.
  const excludedFields = useMemo(
    () =>
      isIndexMode
        ? ["group_column", "train", "test", "validation"]
        : ["group_column"],
    [isIndexMode],
  );

  // The splitter computes the preview, and with it whether the configuration
  // can be used and which partitions receive rows. A predefined split is read
  // from the dataset's own partitions by the backend.
  const {
    preview,
    loading: previewLoading,
    error: previewError,
    errorStatus: previewErrorStatus,
    retry: retryPreview,
  } = useSplitPreview({
    datasetId,
    splitterName: paramsOwned ? splitterName : null,
    params: splitterParams ?? {},
    splitType: isHoldout ? splitType : null,
    indexes:
      isHoldout && splitType === SPLIT_TYPES.MANUAL
        ? rowsPartitionsIndex
        : null,
  });
  // A 422 is the backend's verdict on the configuration, the one creating
  // the session would give; any other failure is the preview's own, and the
  // session API still checks the configuration when it is created.
  const previewFailed = previewError !== null || previewErrorStatus !== null;
  const configurationRefused = previewErrorStatus === 422;
  const previewFailure = previewFailed
    ? { reason: previewError, invalid: configurationRefused }
    : null;
  const previewErrors = preview?.errors ?? [];
  const errorMessages = [
    ...previewErrors.map((error) =>
      t(`experiments:error.${error.key}`, error.values),
    ),
    ...(configurationRefused && previewError ? [previewError] : []),
  ];

  // The generated form reports its values only once the user edits a field, so
  // the schema placeholders are pushed up here: without them a session created
  // without touching the form would carry no splitter parameters at all.
  //
  // The schema is fetched by name rather than read from the shared schema hook
  // on purpose. That hook keeps the previous splitter's schema for one render
  // after the name changes, and seeding from it left the parameters of the
  // splitter that was selected a moment ago in place.
  //
  // The defaults always replace the previous splitter's parameters, even when
  // there are none or the schema cannot be fetched; what the new splitter's
  // form already sent is kept over them.
  useEffect(() => {
    if (!splitterName) return undefined;
    let cancelled = false;

    const seedSplitterParams = async () => {
      let defaults = {};
      try {
        const component = await getComponents({ model: splitterName });
        const properties = component?.schema?.properties ?? {};
        defaults = Object.fromEntries(
          Object.entries(properties)
            .filter(([, property]) => "placeholder" in property)
            .map(([key, property]) => [key, property.placeholder]),
        );
      } catch (error) {
        console.error(`Error fetching the ${splitterName} schema`, error);
      }
      if (cancelled) return;
      const submitted = paramsOwnerRef.current === splitterName;
      setSplitterParams((current) => ({
        ...defaults,
        ...(submitted ? (current ?? {}) : {}),
      }));
      setParamsOwner(splitterName);
    };

    seedSplitterParams();

    return () => {
      cancelled = true;
    };
  }, [splitterName]);

  // Row indexes typed by hand that do not parse. Whether the train partition
  // got any rows is the preview's to say.
  const [manualParseError, setManualParseError] = useState("");

  const [groupColumnError, setGroupColumnError] = useState(true);
  const [taskSplitters, setTaskSplitters] = useState([]);
  const [allowedStrategies, setAllowedStrategies] = useState([]);

  // Update the offered splitters and strategies when the task changes
  useEffect(() => {
    const getSplittersForTask = async () => {
      try {
        const response = await getComponents({
          selectTypes: ["Splitter"],
          relatedComponent: taskName,
        });
        setTaskSplitters(response);

        // Which strategies exist is a property of the task too, so a
        // forecasting session cannot be pointed at one that scores its
        // training partition.
        const strategies = await getComponents({
          selectTypes: ["EvaluationStrategy"],
          relatedComponent: taskName,
        });
        setAllowedStrategies(strategies);
      } catch (error) {
        console.error("Error fetching splitters:", error);
        enqueueSnackbar(t("models:error.fetchingStatisticalTests"), {
          variant: "error",
        });
      }
    };

    getSplittersForTask();
  }, [taskName]);

  const selectedStrategy = findStrategy(allowedStrategies, evaluationStrategy);

  // The splitters a strategy takes are the ones that carve the way it
  // declares, so a holdout splitter never lands in the folds dropdown.
  const allowedSplitters = useMemo(
    () => splittersOf(selectedStrategy, taskSplitters),
    [selectedStrategy, taskSplitters],
  );

  // A strategy starts on the splitter it declares as its default.
  useEffect(() => {
    setSplitter(defaultSplitterOf(selectedStrategy, allowedSplitters));
  }, [allowedSplitters]);

  // Publish the split shape so the rest of the session reads it instead of
  // comparing strategy names.
  useEffect(() => {
    setStrategyKind(strategyKindOf(selectedStrategy));
  }, [selectedStrategy, setStrategyKind]);

  // And for the strategy itself, which the session used to start on by name.
  useEffect(() => {
    if (!allowedStrategies.length) return;
    if (selectedStrategy) return;
    const holdout = allowedStrategies.find(
      (strategy) => strategyKindOf(strategy) === STRATEGY_KINDS.HOLDOUT,
    );
    setEvaluationStrategy((holdout ?? allowedStrategies[0]).name);
  }, [allowedStrategies, selectedStrategy, setEvaluationStrategy]);

  // The partitions with rows decide the metrics the session records. Without
  // a preview to say which (a splitter with none, or a preview that could not
  // be computed), they are the ones the strategy scores.
  const answered = paramsOwned && !previewLoading;
  const withoutPreview = answered && !preview && !configurationRefused;
  const splitPartitions = preview
    ? preview.partitions
    : withoutPreview
      ? (selectedStrategy?.metadata?.scored_splits ?? null)
      : null;
  useEffect(() => {
    setSplitPartitions?.(splitPartitions);
  }, [splitPartitions]);

  const handleSplitTypeChange = (_e, newType) => {
    if (!newType) return;
    setSplitType(newType);

    if (newType === SPLIT_TYPES.MANUAL) {
      const newIndex = { train: [], test: [], validation: [] };
      setRowsPartitionsIndex(newIndex);
      setManualParseError("");
    }
  };

  const handleRowsChange = (event) => {
    const value = event.target.value;
    const id = event.target.id;

    try {
      const rowsIndex = parseRangeToIndex(value, totalRows);
      setRowsPartitionsIndex({ ...rowsPartitionsIndex, [id]: rowsIndex });
      setManualParseError("");
    } catch (error) {
      setManualParseError(error.message);
    }
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

  useEffect(() => {
    if (hasPredefinedSplits) {
      setSplitType(SPLIT_TYPES.PREDEFINED);
    } else {
      setSplitType(SPLIT_TYPES.RANDOM);
    }
  }, [hasPredefinedSplits]);

  const isManual = isHoldout && splitType === SPLIT_TYPES.MANUAL;

  useEffect(() => {
    if (strategyKind === STRATEGY_KINDS.FULL) {
      // Nothing is carved, so there is nothing left to configure.
      setSplitsReady(true);
    } else if (
      !strategyKind ||
      !splitterName ||
      !paramsOwned ||
      paramsError ||
      previewLoading ||
      configurationRefused ||
      (isManual && manualParseError) ||
      (strategyKind === STRATEGY_KINDS.CV && groupColumnError)
    ) {
      setSplitsReady(false);
    } else {
      // Without a preview, the session API checks the configuration.
      setSplitsReady(previewErrors.length === 0);
    }
  }, [
    strategyKind,
    splitterName,
    paramsOwned,
    paramsError,
    previewLoading,
    preview,
    configurationRefused,
    isManual,
    manualParseError,
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
    const isGrouping = Boolean(splitter?.schema?.properties?.group_column);
    if (isGrouping && !groupColumn) {
      setGroupColumnError(true);
    } else {
      setGroupColumnError(false);
    }
  }, [splitter, groupColumn, t]);

  // Typed indexes are reported where they are typed; every other problem
  // under the splitter's form.
  const manualMessage = manualParseError || (isManual && errorMessages[0]);
  const splitsMessage = isManual ? "" : errorMessages.join(" ");

  const splitterSelect = (label) => (
    <SplitsCard label={label}>
      <FormControl fullWidth size="small">
        <Select
          value={splitter ?? ""}
          onChange={(e) => setSplitter(e.target.value)}
        >
          {allowedSplitters.map((type) => (
            <MenuItem key={type.name} value={type}>
              {type.display_name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </SplitsCard>
  );

  return (
    <Stack spacing={4} data-tour="exp-dataset-splits">
      {/* Evaluation Strategy Selector, when the task offers a choice */}
      {allowedStrategies.length > 1 && (
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
              {allowedStrategies.map((strategy) => (
                <ToggleButton
                  key={strategy.name}
                  value={strategy.name}
                  sx={{ textTransform: "none", fontSize: "0.8rem" }}
                >
                  {strategy.display_name ?? strategy.name}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
        </Paper>
      )}

      {/* HOLDOUT SECTION */}
      {strategyKind === STRATEGY_KINDS.HOLDOUT && (
        <>
          {/* Split type selector */}
          <Paper
            variant="outlined"
            sx={{ borderRadius: 2, overflow: "hidden" }}
          >
            <Box
              sx={{
                px: 8,
                py: 3,
                borderBottom: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography variant="body2" fontWeight={600}>
                {t("experiments:label.splitType")}
              </Typography>
            </Box>
            <Box sx={{ px: 8, pt: 2, pb: 4 }}>
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

          {/* Manual */}
          {splitType === SPLIT_TYPES.MANUAL && (
            <SplitsCard
              label={t("experiments:label.rowIndexes")}
              description={t("experiments:label.rowIndexesDescription")}
              errorMessage={manualMessage || undefined}
            >
              <Grid container spacing={2}>
                {splitFields.map(({ id, label }) => (
                  <Grid key={id} size={{ xs: 4 }}>
                    <TextField
                      id={id}
                      label={label}
                      size="small"
                      fullWidth
                      error={Boolean(manualMessage)}
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
      {strategyKind === STRATEGY_KINDS.CV && (
        <>
          {/* CV Type Selector */}
          {splitterSelect(t("experiments:label.cvType"))}

          {/* Group Column */}
          {Boolean(splitter?.schema?.properties?.group_column) && (
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
        </>
      )}

      {/* ANY OTHER STRATEGY: its splitter's own form is all it needs, and the
          splitter to use when it takes more than one */}
      {strategyKind &&
        ![
          STRATEGY_KINDS.HOLDOUT,
          STRATEGY_KINDS.CV,
          STRATEGY_KINDS.FULL,
        ].includes(strategyKind) &&
        allowedSplitters.length > 1 &&
        splitterSelect(t("experiments:label.splitter"))}

      {/* FULL DATASET SECTION: nothing is carved, so there is no splitter to
          choose and no partition to preview */}
      {strategyKind === STRATEGY_KINDS.FULL ? (
        <Alert severity="info">
          {t("experiments:label.noSplitConfigNeeded")}
        </Alert>
      ) : (
        <SplitPreview
          preview={preview}
          loading={previewLoading || (Boolean(splitterName) && !paramsOwned)}
          failure={previewFailure}
          onRetry={retryPreview}
          description={selectedStrategy?.description}
          splitterDescription={splitter?.description}
        />
      )}

      {/* Splitter parameters, generated from the component schema */}
      {splitterName && (
        <>
          <FormSchemaLayout>
            <FormSchema
              autoSave
              hideButtons
              key={splitterName}
              model={splitterName}
              onFormSubmit={submitSplitterParams}
              setError={setParamsError}
              excludeFields={excludedFields}
            />
          </FormSchemaLayout>
          {splitsMessage && (
            <FormHelperText error sx={{ px: 4 }}>
              {splitsMessage}
            </FormHelperText>
          )}
        </>
      )}
    </Stack>
  );
}

SplitDatasetRows.propTypes = {
  datasetId: PropTypes.number,
  datasetInfo: PropTypes.object.isRequired,
  rowsPartitionsIndex: PropTypes.object.isRequired,
  setRowsPartitionsIndex: PropTypes.func.isRequired,
  setSplitsReady: PropTypes.func.isRequired,
  setSplitPartitions: PropTypes.func,
  splitType: PropTypes.string.isRequired,
  setSplitType: PropTypes.func.isRequired,
  SPLIT_TYPES: PropTypes.object.isRequired,
  splitterParams: PropTypes.object,
  setSplitterParams: PropTypes.func.isRequired,
  paramsError: PropTypes.bool,
  setParamsError: PropTypes.func.isRequired,
  evaluationStrategy: PropTypes.string,
  setEvaluationStrategy: PropTypes.func.isRequired,
  splitter: PropTypes.object,
  setSplitter: PropTypes.func.isRequired,
  strategyKind: PropTypes.string,
  setStrategyKind: PropTypes.func,
  groupColumn: PropTypes.string,
  setGroupColumn: PropTypes.func.isRequired,
  inputColumnNames: PropTypes.arrayOf(PropTypes.string),
  taskName: PropTypes.string,
};

export default SplitDatasetRows;
