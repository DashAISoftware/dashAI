import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import {
  Alert,
  AlertTitle,
  Box,
  Grid,
  Link,
  Paper,
  TextField,
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
  defaultName,
  handlePredictNameInput,
  predictName,
  selectedTaskName,
  forecastPeriods,
  setForecastPeriods,
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
    // For ForecastingTask: enable Next if either dataset selected OR forecast_periods provided
    if (isForecastingTask && forecastPeriods > 0) {
      // Auto-generate mode: no dataset needed
      setSelectedDatasetId(null); // Clear dataset selection if forecast_periods is set
      if (preselectedModelId) {
        setNextEnabled(isNameValid);
      } else {
        setNextEnabled(true);
      }
    } else if (datasetsSelected.length > 0) {
      // Dataset upload mode: dataset required
      const selectedDatasetId = datasetsSelected[0];
      setSelectedDatasetId(selectedDatasetId);
      if (preselectedModelId) {
        setNextEnabled(isNameValid);
      } else {
        setNextEnabled(true);
      }
    } else {
      // Neither dataset nor forecast_periods: disable Next
      setNextEnabled(false);
    }
  }, [
    datasetsSelected,
    isNameValid,
    preselectedModelId,
    isForecastingTask,
    forecastPeriods,
  ]);

  return (
    <React.Fragment>
      {preselectedModelId && (
        <Grid item xs={12}>
          <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
            Provide a prediction name to continue and select a dataset
          </Typography>

          <PredictionNameInput
            defaultPredictionName={defaultName}
            onValidChange={setIsNameValid}
            onNameChange={handlePredictNameInput}
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

      {isForecastingTask && (
        <Grid item xs={12} sx={{ mb: 3 }}>
          <TextField
            fullWidth
            type="number"
            label="Auto-generate Future Timestamps (Optional)"
            placeholder="e.g., 30"
            value={forecastPeriods || ""}
            onChange={(e) => {
              const value = e.target.value;
              if (value === "") {
                setForecastPeriods(null);
              } else {
                const numValue = parseInt(value, 10);
                if (numValue > 0 && numValue <= 1000) {
                  setForecastPeriods(numValue);
                }
              }
            }}
            helperText="Number of future periods to forecast from last training date. Leave empty to upload your own dataset with timestamps. Cannot be used with exogenous variables."
            inputProps={{
              min: 1,
              max: 1000,
            }}
          />
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
  defaultName: PropTypes.string,
  handlePredictNameInput: PropTypes.func,
  predictName: PropTypes.string,
  preselectedModelId: PropTypes.number,
  forecastPeriods: PropTypes.number,
  setForecastPeriods: PropTypes.func,
  selectedModelId: PropTypes.number,
};

export default SelectDatasetStep;
