import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { Grid, Paper, Typography, TextField } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { get_model_table } from "../../api/predict";
import { formatDate } from "../../utils";

function SelectModelStep({
  setSelectedModelId,
  setNextEnabled,
  onPredictNameInput,
  setTrainDataset,
  defaultPredictionName,
}) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { enqueueSnackbar } = useSnackbar();
  const [predictName, setPredictName] = useState("");
  const [predictNameError, setPredictNameError] = useState(false);
  const [rowClicked, setRowClicked] = useState(false);
  const [hasUserTouchedName, setHasUserTouchedName] = useState(false);

  const columns = React.useMemo(() => [
    {
      field: "id",
      headerName: "ID",
      minWidth: 10,
      editable: false,
    },

    {
      field: "run_name",
      headerName: "Model Name",
      minWidth: 300,
      editable: false,
    },
    {
      field: "model_name",
      headerName: "Model",
      minWidth: 300,
      editable: false,
    },
    {
      field: "task_name",
      headerName: "Task",
      minWidth: 200,
      editable: false,
    },
    {
      field: "dataset_name",
      headerName: "Dataset Name",
      minWidth: 200,
      editable: false,
    },
    {
      field: "created",
      headerName: "Created",
      minWidth: 170,
      editable: false,
      type: Date,
      valueFormatter: (params) => formatDate(params.value),
    },
  ]);

  const get_Models = async () => {
    setLoading(true);
    setError(null);
    try {
      const models = await get_model_table();
      setModels(models);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the models table.");
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

  const handleRowClick = (params) => {
    setSelectedModelId(params.row.id);
    setTrainDataset(params.row.dataset_id);
    setRowClicked(true);
    validateAndUpdateNextButton(predictName, true);
  };

  const isValidPredictName = (name) => {
    return name.length >= 4 && /^[a-zA-Z0-9_-]+$/.test(name);
  };

  const validateAndUpdateNextButton = useCallback(
    (name, rowIsClicked) => {
      const trimmedName = name.trim();
      let isValid = false;
      let hasError = false;

      if (trimmedName === "") {
        if (hasUserTouchedName) {
          isValid = false;
          hasError = false;
        } else {
          isValid = isValidPredictName(defaultPredictionName || "");
          hasError = false;
        }
      } else {
        isValid = isValidPredictName(trimmedName);
        hasError = !isValid;
      }

      setPredictNameError(hasError);
      setNextEnabled(isValid && (rowIsClicked || rowClicked));
      return isValid;
    },
    [rowClicked, setNextEnabled, defaultPredictionName, hasUserTouchedName],
  );

  const handlePredictNameInput = useCallback(
    (event) => {
      const value = event.target.value;
      setHasUserTouchedName(true);
      setPredictName(value);
      onPredictNameInput(value);
      validateAndUpdateNextButton(value, rowClicked);
    },
    [rowClicked, onPredictNameInput, validateAndUpdateNextButton],
  );

  useEffect(() => {
    setNextEnabled(false);
  }, []);

  useEffect(() => {
    if (defaultPredictionName && !predictName.trim() && !hasUserTouchedName) {
      setPredictName(defaultPredictionName);
      onPredictNameInput(defaultPredictionName);
    }
  }, [
    defaultPredictionName,
    onPredictNameInput,
    hasUserTouchedName,
    predictName,
  ]);

  useEffect(() => {
    get_Models();
  }, []);

  return (
    <Grid
      container
      direction="row"
      justifyContent="space-around"
      alignItems="stretch"
      spacing={2}
    >
      <Grid size={{ xs: 12 }}>
        <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
          Provide a prediction name and select a model
        </Typography>

        <TextField
          id="predict-name-input"
          label="Prediction name"
          value={predictName}
          fullWidth
          onChange={handlePredictNameInput}
          autoComplete="off"
          sx={{ mb: 4 }}
          error={
            !!((predictName === "" && hasUserTouchedName) || predictNameError)
          }
          helperText={
            predictName === "" && hasUserTouchedName
              ? "Name is required"
              : predictNameError
                ? "The prediction name must have at least 4 alphanumeric characters."
                : ""
          }
          slotProps={{
            inputLabel: { shrink: true },
          }}
        />
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Paper sx={{ height: 400, width: "100%" }}>
          <Typography variant="h6" component="h2" sx={{ pl: 2, pt: 1 }}>
            Select a Model
          </Typography>
          <Typography
            variant="subtitle1"
            component="h3"
            sx={{ p: 1 }}
            color="text.secondary"
          >
            Select a model to proceed
          </Typography>
          <DataGrid
            rows={models}
            columns={columns}
            pageSize={5}
            rowsPerPageOptions={[5]}
            onRowClick={handleRowClick}
          />
        </Paper>
      </Grid>
    </Grid>
  );
}

SelectModelStep.propTypes = {
  setSelectedModelId: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  onPredictNameInput: PropTypes.func.isRequired,
  setTrainDataset: PropTypes.func.isRequired,
  defaultPredictionName: PropTypes.string,
};

export default SelectModelStep;
