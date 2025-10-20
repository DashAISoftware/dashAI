import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import { Grid, Paper, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { get_model_table } from "../../api/predict";
import { formatDate } from "../../utils";
import PredictionNameInput from "./PredictionNameInput";

function SelectModelStep({
  setSelectedModelId,
  setNextEnabled,
  onPredictNameInput,
  setTrainDataset,
  defaultPredictionName,
}) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const [rowClicked, setRowClicked] = useState(false);
  const [isNameValid, setIsNameValid] = useState(false);

  const columns = useMemo(
    () => [
      { field: "id", headerName: "ID", minWidth: 10 },
      { field: "run_name", headerName: "Model Name", minWidth: 300 },
      { field: "model_name", headerName: "Model", minWidth: 300 },
      { field: "task_name", headerName: "Task", minWidth: 200 },
      { field: "dataset_name", headerName: "Dataset Name", minWidth: 200 },
      {
        field: "created",
        headerName: "Created",
        minWidth: 170,
        type: Date,
        valueGetter: (value) => formatDate(value),
      },
    ],
    [],
  );

  const get_Models = async () => {
    setLoading(true);
    try {
      const models = await get_model_table();
      setModels(models);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the models table.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = (params) => {
    setSelectedModelId(params.row.id);
    setTrainDataset(params.row.dataset_id);
    setRowClicked(true);
  };

  // enable Next if both name is valid and a row is selected
  useEffect(() => {
    setNextEnabled(isNameValid && rowClicked);
  }, [isNameValid, rowClicked, setNextEnabled]);

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

        <PredictionNameInput
          defaultPredictionName={defaultPredictionName}
          onValidChange={setIsNameValid}
          onNameChange={onPredictNameInput}
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
