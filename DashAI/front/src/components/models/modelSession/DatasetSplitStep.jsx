import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import { Grid, CircularProgress, Box, Alert, AlertTitle } from "@mui/material";
import SplitDatasetRows from "./SplitDatasetRows";
import {
  getDatasetInfo as getDatasetInfoRequest,
  getDatasetTypes as getDatasetTypesRequest,
} from "../../../api/datasets";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { useModels } from "../ModelsContext";
/**
 * Step of the experiment modal: Set the splits for training, validation and
 * testing.
 * @param {object} newExp object that contains the Experiment Modal state
 * @param {function} setNewExp updates the Eperimento Modal state (newExp)
 * @param {function} setNextEnabled function to enable or disable the "Next" button in the modal
 * @param {string} evaluationStrategy the evaluation strategy selected for the experiment, either holdout or cross-validation
 * @param {function} setEvaluationStrategy function to update the evaluation strategy in the parent component (CreateSessionSteps)
 */
function DatasetSplitStep({
  newExp,
  setNewExp,
  setNextEnabled,
  dataset,
  evaluationStrategy,
  setEvaluationStrategy,
  isActive = true,
}) {
  const { setSessionRightContent } = useModels();
  const [datasetInfo, setDatasetInfo] = useState({});
  const [datasetTypes, setDatasetTypes] = useState({});
  const { enqueueSnackbar } = useSnackbar();
  const [infoLoading, setInfoLoading] = useState(true);
  const { t } = useTranslation(["experiments", "common"]);

  const [shuffle, setShuffle] = useState(true);
  const [stratify, setStratify] = useState(false);
  const [seed, setSeed] = useState(42);

  // Cross-Validation configuration states
  const [cvType, setCvType] = useState(null);
  const [numFolds, setNumFolds] = useState(5);
  const [numRepeats, setNumRepeats] = useState(2);
  const [groupColumn, setGroupColumn] = useState("");

  const defaultParitionsIndex = {
    train: [],
    validation: [],
    test: [],
  };
  const defaultPartitionsPercentage = {
    train: 0.6,
    validation: 0.2,
    test: 0.2,
  };

  const [datasetPartitionsIndex, setDatasetPartitionsIndex] = useState({});

  const [rowsPartitionsIndex, setRowsPartitionsIndex] = useState(
    defaultParitionsIndex,
  );
  const [rowsPartitionsPercentage, setRowsPartitionsPercentage] = useState(
    defaultPartitionsPercentage,
  );
  const SPLIT_TYPES = {
    RANDOM: "random",
    MANUAL: "manual",
    PREDEFINED: "predefined",
  };
  const [splitType, setSplitType] = useState("");

  const [splitsReady, setSplitsReady] = useState(false);

  const getDatasetInfo = async () => {
    if (!dataset?.id) return;
    setInfoLoading(true);
    try {
      const [fetchedDatasetInfo, fetchedDatasetTypes] = await Promise.all([
        getDatasetInfoRequest(dataset.id),
        getDatasetTypesRequest(dataset.id),
      ]);
      setDatasetInfo(fetchedDatasetInfo);
      setDatasetTypes(fetchedDatasetTypes);

      if (fetchedDatasetInfo) {
        setDatasetPartitionsIndex({
          train: fetchedDatasetInfo.train_indices || [],
          validation: fetchedDatasetInfo.val_indices || [],
          test: fetchedDatasetInfo.test_indices || [],
        });
      }
    } catch (error) {
      enqueueSnackbar(t("experiments:error.errorFetchingDatasetInfo"));
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setInfoLoading(false);
    }
  };

  const updateExperiment = () => {
    if (
      !datasetInfo ||
      !datasetInfo.column_names ||
      datasetInfo.column_names.length === 0
    ) {
      return;
    }

    const updatedExpData = {
      ...newExp,
      evaluation_strategy: evaluationStrategy,
    };

    if (evaluationStrategy === "HoldoutEvaluationStrategy") {
      if (splitType === SPLIT_TYPES.MANUAL) {
        updatedExpData.splits = {
          ...rowsPartitionsIndex,
          splitter_name: "HoldoutSplitter",
          splitType: splitType,
        };
      } else if (splitType === SPLIT_TYPES.RANDOM) {
        updatedExpData.splits = {
          ...rowsPartitionsPercentage,
          shuffle: shuffle,
          stratify: stratify,
          seed: seed === "" || seed == null ? 42 : Number(seed),
          splitter_name: "HoldoutSplitter",
          splitType: splitType,
        };
      } else if (splitType === SPLIT_TYPES.PREDEFINED) {
        updatedExpData.splits = {
          ...datasetPartitionsIndex,
          splitter_name: "HoldoutSplitter",
          splitType: splitType,
        };
      }
    } else if (evaluationStrategy === "CrossValidationEvaluationStrategy") {
      const cvSchemaProperties = cvType.schema?.properties || {};
      updatedExpData.splits = {
        splitter_name: cvType.name,
        seed: seed === "" || seed == null ? 42 : Number(seed),
        ...(cvSchemaProperties.n_splits ? { n_splits: numFolds } : {}),
        ...(cvSchemaProperties.n_repeats ? { n_repeats: numRepeats } : {}),
        ...(cvSchemaProperties.group_column
          ? { group_column: groupColumn }
          : {}),
        ...(cvSchemaProperties.shuffle ? { shuffle: shuffle } : {}),
      };
    }

    setNewExp(updatedExpData);
  };

  useEffect(() => {
    if (splitsReady) {
      updateExperiment();
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [
    splitsReady,
    splitType,
    shuffle,
    stratify,
    seed,
    cvType,
    numFolds,
    numRepeats,
    groupColumn,
    evaluationStrategy,
  ]);

  useEffect(() => {
    getDatasetInfo();
  }, [dataset?.id]);

  // Push SplitDatasetRows (or loading spinner) into the right bar. Gated on
  // `isActive`: this component now stays mounted (hidden via CSS, not
  // unmounted) while the wizard's preprocessing step is showing, so it must
  // not fight that step for the sessionRightContent slot — and must
  // reclaim it (hence `isActive` in the deps) whenever the user comes back.
  useEffect(() => {
    if (!isActive) return;
    if (infoLoading) {
      setSessionRightContent(
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            height: "100%",
          }}
        >
          <CircularProgress size={32} />
        </Box>,
      );
      return () => setSessionRightContent(null);
    }
    setSessionRightContent(
      <SplitDatasetRows
        datasetInfo={datasetInfo}
        rowsPartitionsIndex={rowsPartitionsIndex}
        setRowsPartitionsIndex={setRowsPartitionsIndex}
        rowsPartitionsPercentage={rowsPartitionsPercentage}
        setRowsPartitionsPercentage={setRowsPartitionsPercentage}
        setSplitsReady={setSplitsReady}
        splitType={splitType}
        setSplitType={setSplitType}
        SPLIT_TYPES={SPLIT_TYPES}
        shuffle={shuffle}
        setShuffle={setShuffle}
        stratify={stratify}
        setStratify={setStratify}
        seed={seed}
        setSeed={setSeed}
        evaluationStrategy={evaluationStrategy}
        setEvaluationStrategy={setEvaluationStrategy}
        cvType={cvType}
        setCvType={setCvType}
        numFolds={numFolds}
        setNumFolds={setNumFolds}
        numRepeats={numRepeats}
        setNumRepeats={setNumRepeats}
        groupColumn={groupColumn}
        setGroupColumn={setGroupColumn}
        inputColumnNames={datasetInfo.column_names || []}
        taskName={newExp.task_name}
      />,
    );
    return () => setSessionRightContent(null);
  }, [
    infoLoading,
    datasetInfo,
    rowsPartitionsIndex,
    rowsPartitionsPercentage,
    splitType,
    shuffle,
    stratify,
    seed,
    evaluationStrategy,
    cvType,
    numFolds,
    numRepeats,
    groupColumn,
    isActive,
  ]);

  return (
    <React.Fragment>
      {!infoLoading && datasetInfo.nan ? (
        Object.values(datasetInfo.nan).some((v) => v > 0) ? (
          <Alert
            severity="warning"
            sx={{
              mb: 2,
              "& .MuiAlert-icon": { fontSize: 24 },
              bgcolor: (theme) => `${theme.palette.warning.main}40`,
              border: (theme) => `1px solid ${theme.palette.warning.main}`,
            }}
          >
            <AlertTitle>
              {t("experiments:label.missingValuesDetected")}
            </AlertTitle>
            <Grid container spacing={4}>
              {Object.entries(datasetInfo.nan)
                .filter(([_, count]) => count > 0)
                .map(([col, count]) => (
                  <Grid size={{ xs: 12 }} key={col}>
                    - {col}: {count} {t("experiments:label.missingValues")}
                  </Grid>
                ))}
            </Grid>
            <p>{t("experiments:label.recommendPreprocessMissingValues")}</p>
          </Alert>
        ) : null
      ) : null}
    </React.Fragment>
  );
}

DatasetSplitStep.propTypes = {
  newExp: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    dataset: PropTypes.object,
    task_name: PropTypes.string,
    splits: PropTypes.object,
    step: PropTypes.string,
    created: PropTypes.instanceOf(Date),
    last_modified: PropTypes.instanceOf(Date),
    runs: PropTypes.array,
  }),
  setNewExp: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  dataset: PropTypes.object.isRequired,
  isActive: PropTypes.bool,
};
export default DatasetSplitStep;
