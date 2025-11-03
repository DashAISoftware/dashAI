import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import { Grid, CircularProgress, Box, Alert, AlertTitle } from "@mui/material";
import DivideDatasetColumns from "./DivideDatasetColumns";
import SplitDatasetRows from "./SplitDatasetRows";
import { getDatasetInfo as getDatasetInfoRequest } from "../../api/datasets";
import { getComponents as getComponentsRequest } from "../../api/component";
import { validateColumns as validateColumnsRequest } from "../../api/experiment";
import { useSnackbar } from "notistack";
/**
 * Step of the experiment modal: Set the input and output columns to use for clasification
 * and the splits for training, validation and testing
 * @param {object} newExp object that contains the Experiment Modal state
 * @param {function} setNewExp updates the Eperimento Modal state (newExp)
 * @param {function} setNextEnabled function to enable or disable the "Next" button in the modal
 */
function PrepareDatasetStep({ newExp, setNewExp, setNextEnabled }) {
  const [datasetInfo, setDatasetInfo] = useState({});
  const { enqueueSnackbar } = useSnackbar();
  const [infoLoading, setInfoLoading] = useState(true);

  const [taskRequirements, setTaskRequirements] = useState({
    name: "",
    metadata: {
      inputs_types: [],
      inputs_cardinality: "",
      outputs_types: [],
      outputs_cardinality: "",
    },
  });

  const [inputColumnNames, setInputColumnNames] = useState([]);
  const [outputColumnNames, setOutputColumnNames] = useState([]);
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
      const fetchedDatasetInfo = await getDatasetInfoRequest(newExp.dataset.id);
      setDatasetInfo(fetchedDatasetInfo);

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
        } else if (
          newExp.input_columns &&
          newExp.input_columns.length > 0 &&
          allNames.length > 0
        ) {
          setInputColumnNames(
            newExp.input_columns
              .map((index) => allNames[index])
              .filter((name) => name !== undefined),
          );
        }

        if (
          outputColumnNames.length === 0 &&
          (!newExp.output_columns || newExp.output_columns.length === 0)
        ) {
          if (allNames.length > 0) {
            setOutputColumnNames([allNames[allNames.length - 1]]);
          }
        } else if (
          newExp.output_columns &&
          newExp.output_columns.length > 0 &&
          allNames.length > 0
        ) {
          setOutputColumnNames(
            newExp.output_columns
              .map((index) => allNames[index])
              .filter((name) => name !== undefined),
          );
        }
      }
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset info.");
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
        enqueueSnackbar(`Task requirements for ${newExp.task_name} not found.`);
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
      enqueueSnackbar("Error while trying to obtain the task requirements.");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    }
  };

  const getIndicesFromNames = (selectedNames, allNames) => {
    if (
      !allNames ||
      allNames.length === 0 ||
      !selectedNames ||
      selectedNames.length === 0
    )
      return [];
    return selectedNames
      .map((name) => {
        const index = allNames.indexOf(name);
        return index !== -1 ? index + 1 : -1;
      })
      .filter((index) => index !== -1);
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

    const inputIndices = getIndicesFromNames(
      inputColumnNames,
      datasetInfo.column_names,
    );
    const outputIndices = getIndicesFromNames(
      outputColumnNames,
      datasetInfo.column_names,
    );

    if (inputIndices.length === 0 || outputIndices.length === 0) {
      setColumnsAreValid(false);
      return;
    }

    try {
      const validation = await validateColumnsRequest(
        newExp.task_name,
        newExp.dataset.id,
        inputIndices,
        outputIndices,
      );
      setColumnsAreValid(validation.dataset_status === "valid");
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the columns validation.");
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

    const inputIndices = getIndicesFromNames(
      inputColumnNames,
      datasetInfo.column_names,
    );
    const outputIndices = getIndicesFromNames(
      outputColumnNames,
      datasetInfo.column_names,
    );

    const updatedExpData = {
      ...newExp,
      input_columns: inputIndices,
      output_columns: outputIndices,
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

  const parseListOfStrings = (stringsList) => {
    if (!stringsList || stringsList.length === 0) return "any";
    return stringsList.join(" or ");
  };

  return (
    <React.Fragment>
      <Alert severity={columnsAreValid ? "success" : "error"} sx={{ mb: 1 }}>
        <AlertTitle>
          {columnsAreValid
            ? "Current Input and Output columns match"
            : "Current Input and Output columns doesn't match"}{" "}
          {taskRequirements.display_name} requirements
        </AlertTitle>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12 }}>
            The input columns must be of the types{" "}
            {taskRequirements
              ? parseListOfStrings(taskRequirements.metadata.inputs_types)
              : null}
            , and they should have a cardinality of{" "}
            {taskRequirements.metadata.inputs_cardinality}.
          </Grid>
          <Grid size={{ xs: 12 }}>
            The output columns must be of the types{" "}
            {taskRequirements
              ? parseListOfStrings(taskRequirements.metadata.outputs_types)
              : null}
            , and they should have a cardinality of{" "}
            {taskRequirements.metadata.outputs_cardinality}.
          </Grid>
        </Grid>
      </Alert>
      {!infoLoading && datasetInfo.nan ? (
        Object.values(datasetInfo.nan).some((v) => v > 0) ? (
          <Alert severity="warning" sx={{ mb: 1 }}>
            <AlertTitle>
              The dataset contains missing values (NaN) in the columns:
            </AlertTitle>
            <Grid container spacing={2}>
              {Object.entries(datasetInfo.nan)
                .filter(([_, count]) => count > 0)
                .map(([col, count]) => (
                  <Grid item xs={12} key={col}>
                    - {col}: {count} missing values
                  </Grid>
                ))}
            </Grid>
            <p>
              It's recommended to preprocess the dataset to handle these missing
              values before training a model.
            </p>
          </Alert>
        ) : null
      ) : null}

      {!infoLoading ? (
        <Grid container spacing={1}>
          <DivideDatasetColumns
            allColumnNames={datasetInfo.column_names || []}
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
    input_columns: PropTypes.arrayOf(PropTypes.number),
    output_columns: PropTypes.arrayOf(PropTypes.number),
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
