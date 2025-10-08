import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import { Grid, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { Link as RouterLink } from "react-router-dom";
import PredictionNameInput from "./PredictionNameInput";

import { filter_datasets as filterDatasetsRequest } from "../../api/predict";
import { formatDate } from "../../utils";
import PredictionType from "./PredictionType";

const columns = [
  {
    field: "name",
    headerName: "Name",
    minWidth: 250,
    editable: false,
  },
  {
    field: "created",
    headerName: "Created",
    minWidth: 200,
    type: Date,
    valueFormatter: (params) => formatDate(params.value),
    editable: false,
  },
  {
    field: "last_modified",
    headerName: "Last modified",
    minWidth: 200,
    type: Date,
    valueFormatter: (params) => formatDate(params.value),
    editable: false,
  },
];

function SelectDatasetStep({
  selectedModelId,
  preselectedModelId,
  setSelectedDatasetId,
  setNextEnabled,
  trainDataset,
  defaultPredictionName,
  onPredictNameInput,
  setManualInputData,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [datasetsSelected, setDatasetsSelected] = useState([]);
  const [requestError, setRequestError] = useState(false);
  const [isNameValid, setIsNameValid] = useState(false);

  const getDatasets = async () => {
    setLoading(true);
    try {
      const requestData = {
        run_id: preselectedModelId ?? selectedModelId,
      };
      const filteredDatasets = await filterDatasetsRequest(requestData);
      setDatasets(filteredDatasets);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the datasets list.");
      setRequestError(true);

      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getDatasets();
  }, []);

  useEffect(() => {
    if (datasetsSelected.length > 0) {
      // the index of the table start with 1!
      // const dataset = datasets[datasetsSelected[0] - 1];
      const selectedDatasetId = datasetsSelected[0];
      setSelectedDatasetId(selectedDatasetId);
      if (preselectedModelId) {
        setNextEnabled(isNameValid);
      } else {
        setNextEnabled(true);
      }
    }
  }, [datasetsSelected, isNameValid, preselectedModelId]);

  return (
    <React.Fragment>
      {preselectedModelId && (
        <Grid item xs={12}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
            Provide a prediction name to continue and select a dataset
          </Typography>

          <PredictionNameInput
            defaultPredictionName={defaultPredictionName}
            onValidChange={setIsNameValid}
            onNameChange={onPredictNameInput}
          />
        </Grid>
      )}
      {!loading && (
        <PredictionType
          runId={preselectedModelId ?? selectedModelId}
          datasets={datasets}
          columns={columns}
          loading={loading}
          requestError={requestError}
          setDatasetsSelected={setDatasetsSelected}
          datasetsSelected={datasetsSelected}
          setManualInputData={setManualInputData}
        />
      )}
    </React.Fragment>
  );
}

SelectDatasetStep.propTypes = {
  setSelectedDatasetId: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  trainDataset: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    .isRequired,
};

export default SelectDatasetStep;
