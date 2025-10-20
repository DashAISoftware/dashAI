import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import {
  Alert,
  AlertTitle,
  Box,
  Grid,
  Link,
  Paper,
  Typography,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { Link as RouterLink } from "react-router-dom";
import PredictionNameInput from "./PredictionNameInput";
import InfoIcon from "@mui/icons-material/Info";

import { getDatasets as getDatasetsRequest } from "../../api/datasets";

import { filter_datasets as filterDatasetsRequest } from "../../api/predict";
import { formatDate } from "../../utils";

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
  selectedTaskName,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [datasetsSelected, setDatasetsSelected] = useState([]);
  const [requestError, setRequestError] = useState(false);
  const [isNameValid, setIsNameValid] = useState(false);

  const isForecastingTask = selectedTaskName === "ForecastingTask";

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

      {isForecastingTask && (
        <Grid item xs={12} sx={{ mb: 2 }}>
          <Alert severity="info" icon={<InfoIcon />}>
            <AlertTitle>Forecast Requirements</AlertTitle>
            <Typography variant="body2" component="div">
              <strong>For forecasting predictions:</strong>
              <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
                <li>
                  Dataset must include a <strong>ds</strong> (timestamp) column
                  with dates to predict (past, present, or future)
                </li>
                <li>
                  Timestamps must be <strong>strictly increasing</strong> and
                  match the training frequency
                </li>
                <li>
                  If the model used exogenous regressors during training,
                  include those columns with values for all timestamps
                </li>
                <li>
                  Any <strong>y</strong> (target) column will be ignored during
                  prediction
                </li>
              </ul>
            </Typography>
          </Alert>
        </Grid>
      )}

      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 4 }}
      >
        <Typography variant="subtitle1" component="h3">
          Select a dataset for the selected task
        </Typography>
      </Grid>
      {datasets.length === 0 && !loading && !requestError && (
        <React.Fragment>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <AlertTitle>There is no datasets available.</AlertTitle>
            Go to{" "}
            <Link component={RouterLink} to="/app/data">
              data tab
            </Link>{" "}
            to upload one first.
          </Alert>
          <Typography></Typography>
        </React.Fragment>
      )}
      <Paper>
        <DataGrid
          rows={datasets}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 10,
              },
            },
          }}
          onRowSelectionModelChange={(newRowSelectionModel) => {
            setDatasetsSelected(newRowSelectionModel);
          }}
          rowSelectionModel={datasetsSelected}
          density="compact"
          pageSizeOptions={[10]}
          loading={loading}
          autoHeight
          hideFooterSelectedRowCount
        />
      </Paper>
    </React.Fragment>
  );
}

SelectDatasetStep.propTypes = {
  setSelectedDatasetId: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  trainDataset: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    .isRequired,
  selectedTaskName: PropTypes.string,
};

export default SelectDatasetStep;
