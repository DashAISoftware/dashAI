import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import {
  Grid,
  CircularProgress,
  Box,
  Alert,
  AlertTitle,
  Chip,
} from "@mui/material";
import DivideDatasetColumns from "./DivideDatasetColumns";
import SplitDatasetRows from "./SplitDatasetRows";
import {
  getDatasetInfo as getDatasetInfoRequest,
  getDatasetTypes as getDatasetTypesRequest,
} from "../../api/datasets";
import { getComponents as getComponentsRequest } from "../../api/component";
import { validateColumns as validateColumnsRequest } from "../../api/modelSession";
import { useSnackbar } from "notistack";
import { getColorByColumnType } from "../../utils";
import { useTranslation } from "react-i18next";
import { Trans } from "react-i18next";

/**
 * Renders a list of column type names as colored chips joined by "or".
 * @param {string[]} typesList - List of type names to render
 * @param {function} t - i18next translation function
 */
function renderTypesAsChips(typesList, t) {
  if (!typesList || typesList.length === 0) {
    return <span>{t("common:any")}</span>;
  }

  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        gap: 0.5,
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      {typesList.map((type, index) => (
        <React.Fragment key={type}>
          <Chip
            label={type}
            size="small"
            sx={{
              backgroundColor: getColorByColumnType(type),
              color: "#fff",
              fontWeight: 600,
              fontSize: "0.75rem",
              height: "22px",
            }}
          />
          {index < typesList.length - 1 && (
            <span style={{ margin: "0 4px" }}>{t("common:or")}</span>
          )}
        </React.Fragment>
      ))}
    </Box>
  );
}

/**
 * Step of the experiment modal: Set the input and output columns to use for clasification
 * and the splits for training, validation and testing
 * @param {object} newExp object that contains the Experiment Modal state
 * @param {function} setNewExp updates the Eperimento Modal state (newExp)
 * @param {function} setNextEnabled function to enable or disable the "Next" button in the modal
 */
function PrepareDatasetStep({ newExp, setNewExp, setNextEnabled }) {
  const [datasetInfo, setDatasetInfo] = useState({});
  const [datasetTypes, setDatasetTypes] = useState({});
  const { enqueueSnackbar } = useSnackbar();
  const [infoLoading, setInfoLoading] = useState(true);
  const { t } = useTranslation(["experiments", "common"]);

  const [taskRequirements, setTaskRequirements] = useState({
    name: "",
    metadata: {
      inputs_types: [],
      inputs_cardinality: "",
      outputs_types: [],
      outputs_cardinality: "",
    },
  });

  const [inputColumnNames, setInputColumnNames] = useState(
    newExp.input_columns,
  );
  const [outputColumnNames, setOutputColumnNames] = useState(
    newExp.output_columns,
  );

  const [columnsReady, setColumnsReady] = useState(false);
  const [columnsAreValid, setColumnsAreValid] = useState(false);
  const [shuffle, setShuffle] = useState(true);
  const [stratify, setStratify] = useState(false);
  const [seed, setSeed] = useState();

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
    setInfoLoading(true);
    try {
      const [fetchedDatasetInfo, fetchedDatasetTypes] = await Promise.all([
        getDatasetInfoRequest(newExp.dataset.id),
        getDatasetTypesRequest(newExp.dataset.id),
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

      if (
        fetchedDatasetInfo &&
        fetchedDatasetInfo.column_names &&
        fetchedDatasetInfo.column_names.length > 0
      ) {
        const allNames = fetchedDatasetInfo.column_names;
        if (
          inputColumnNames.length === 0 &&
          (!newExp.input_columns || newExp.input_columns.length === 0)
        ) {
          if (allNames.length > 1) {
            setInputColumnNames(allNames.slice(0, -1));
          } else if (allNames.length === 1) {
            setInputColumnNames([allNames[0]]);
          }
        }

        if (
          outputColumnNames.length === 0 &&
          (!newExp.output_columns || newExp.output_columns.length === 0)
        ) {
          if (allNames.length > 0) {
            setOutputColumnNames([allNames[allNames.length - 1]]);
          }
        }
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

  const getTaskRequirements = async () => {
    try {
      const taskComponents = await getComponentsRequest({
        selectTypes: ["Task"],
      });

      const currentTask = taskComponents.find(
        (task) => task.name === newExp.task_name,
      );
      if (currentTask) {
        setTaskRequirements(currentTask);
      } else {
        enqueueSnackbar(
          t("experiments:error.taskRequirementsNotFound", {
            taskName: newExp.task_name,
          }),
        );
        setTaskRequirements({
          name: newExp.task_name,
          metadata: {
            inputs_types: [],
            inputs_cardinality: "",
            outputs_types: [],
            outputs_cardinality: "",
          },
        });
      }
    } catch (error) {
      enqueueSnackbar(t("experiments:error.errorFetchingTaskRequirements"));
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const validateColumns = async () => {
    if (
      !datasetInfo ||
      !datasetInfo.column_names ||
      datasetInfo.column_names.length === 0
    ) {
      setColumnsAreValid(false);
      return;
    }

    if (inputColumnNames.length === 0 || outputColumnNames.length === 0) {
      setColumnsAreValid(false);
      return;
    }

    try {
      const validation = await validateColumnsRequest(
        newExp.task_name,
        newExp.dataset.id,
        inputColumnNames,
        outputColumnNames,
      );
      setColumnsAreValid(validation.dataset_status === "valid");
    } catch (error) {
      enqueueSnackbar(t("experiments:error.errorFetchingColumnsValidation"));
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
      setColumnsAreValid(false);
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
      input_columns: inputColumnNames,
      output_columns: outputColumnNames,
    };

    if (splitType === SPLIT_TYPES.MANUAL) {
      updatedExpData.splits = {
        ...rowsPartitionsIndex,
        splitType: splitType,
      };
    } else if (splitType === SPLIT_TYPES.RANDOM) {
      updatedExpData.splits = {
        ...rowsPartitionsPercentage,
        shuffle: shuffle,
        stratify: stratify,
        seed: seed === "" || seed == null ? 42 : Number(seed),
        splitType: splitType,
      };
    } else if (splitType === SPLIT_TYPES.PREDEFINED) {
      updatedExpData.splits = {
        ...datasetPartitionsIndex,
        splitType: splitType,
      };
    }
    setNewExp(updatedExpData);
  };

  useEffect(() => {
    if (inputColumnNames.length >= 1 && outputColumnNames.length >= 1) {
      setColumnsReady(true);
    } else {
      setColumnsReady(false);
    }
  }, [inputColumnNames, outputColumnNames]);

  useEffect(() => {
    if (
      columnsReady &&
      splitsReady &&
      datasetInfo &&
      datasetInfo.column_names &&
      datasetInfo.column_names.length > 0
    ) {
      validateColumns();
    } else {
      setColumnsAreValid(false);
    }
  }, [
    columnsReady,
    splitsReady,
    inputColumnNames,
    outputColumnNames,
    datasetInfo,
  ]);

  useEffect(() => {
    if (columnsAreValid && splitsReady && columnsReady) {
      updateExperiment();
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [
    columnsReady,
    splitsReady,
    columnsAreValid,
    splitType,
    shuffle,
    stratify,
    seed,
    inputColumnNames,
    outputColumnNames,
  ]);

  useEffect(() => {
    getDatasetInfo();
    getTaskRequirements();
  }, []);

  return (
    <React.Fragment>
      <Alert
        severity={columnsAreValid ? "success" : "error"}
        sx={{ mb: 1 }}
        data-tour="models-validation-alert"
      >
        <AlertTitle>
          {taskRequirements
            ? t(
                columnsAreValid
                  ? "experiments:label.columnsValidRequirements"
                  : "experiments:label.columnsInvalidRequirements",
                { taskName: taskRequirements.display_name },
              )
            : null}
        </AlertTitle>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                flexWrap: "wrap",
              }}
            >
              <Trans i18nKey="experiments:label.datasetInputColumnRequirements">
                <span>The input columns must be of the types</span>
                {taskRequirements
                  ? renderTypesAsChips(
                      taskRequirements.metadata.inputs_types,
                      t,
                    )
                  : null}
                <span>
                  , and they should have a cardinality of
                  <span>
                    {{
                      cardinality: taskRequirements.metadata.inputs_cardinality,
                    }}
                    .
                  </span>
                </span>
              </Trans>
            </Box>
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                flexWrap: "wrap",
              }}
            >
              <Trans i18nKey="experiments:label.datasetOutputColumnRequirements">
                <span>The output columns must be of the types</span>
                {taskRequirements
                  ? renderTypesAsChips(
                      taskRequirements.metadata.outputs_types,
                      t,
                    )
                  : null}
                <span>
                  , and they should have a cardinality of
                  {{
                    cardinality: taskRequirements.metadata.outputs_cardinality,
                  }}
                  .
                </span>
              </Trans>
            </Box>
          </Grid>
        </Grid>
      </Alert>
      {!infoLoading && datasetInfo.nan ? (
        Object.values(datasetInfo.nan).some((v) => v > 0) ? (
          <Alert severity="warning" sx={{ mb: 1 }}>
            <AlertTitle>
              {t("experiments:label.missingValuesDetected")}
            </AlertTitle>
            <Grid container spacing={2}>
              {Object.entries(datasetInfo.nan)
                .filter(([_, count]) => count > 0)
                .map(([col, count]) => (
                  <Grid item xs={12} key={col}>
                    - {col}: {count} {t("experiments:label.missingValues")}
                  </Grid>
                ))}
            </Grid>
            <p>{t("experiments:label.recommendPreprocessMissingValues")}</p>
          </Alert>
        ) : null
      ) : null}

      {!infoLoading ? (
        <Grid container spacing={1}>
          <DivideDatasetColumns
            allColumnNames={datasetInfo.column_names || []}
            columnTypes={datasetTypes}
            selectedInputColumnNames={inputColumnNames}
            onInputColumnNamesChange={setInputColumnNames}
            selectedOutputColumnNames={outputColumnNames}
            onOutputColumnNamesChange={setOutputColumnNames}
            disabled={
              infoLoading || (datasetInfo.column_names || []).length === 0
            }
          />

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
          />
        </Grid>
      ) : (
        <Box sx={{ display: "flex", justifyContent: "center" }}>
          <CircularProgress />
        </Box>
      )}
    </React.Fragment>
  );
}

PrepareDatasetStep.propTypes = {
  newExp: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    dataset: PropTypes.object,
    task_name: PropTypes.string,
    input_columns: PropTypes.arrayOf(PropTypes.string),
    output_columns: PropTypes.arrayOf(PropTypes.string),
    splits: PropTypes.object,
    step: PropTypes.string,
    created: PropTypes.instanceOf(Date),
    last_modified: PropTypes.instanceOf(Date),
    runs: PropTypes.array,
  }),
  setNewExp: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};
export default PrepareDatasetStep;
