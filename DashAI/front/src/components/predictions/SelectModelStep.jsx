import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import { Grid, Paper, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { get_model_table } from "../../api/predict";
import { formatDate } from "../../utils";
import PredictionNameInput from "./PredictionNameInput";
import { getComponents } from "../../api/component";

function SelectModelStep({
  setSelectedModelId,
  setNextEnabled,
  onPredictNameInput,
  setTrainDataset,
  defaultPredictionName,
}) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const [rowClicked, setRowClicked] = useState(false);
  const [isNameValid, setIsNameValid] = useState(false);
  const [models, setModels] = useState([]);
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    const fetchModelsAndTasks = async () => {
      try {
        const [modelsData, tasksData] = await Promise.all([
          getComponents({ selectTypes: ["Model"] }),
          getComponents({ selectTypes: ["Task"] }),
        ]);
        setModels(modelsData);
        setTasks(tasksData);
      } catch (error) {
        console.error("Error fetching models or tasks:", error);
      }
    };
    fetchModelsAndTasks();
  }, []);

  const columns = useMemo(
    () => [
      { field: "id", headerName: "ID", minWidth: 10 },
      { field: "run_name", headerName: "Model Name", minWidth: 300 },
      {
        field: "model_name",
        headerName: "Model",
        minWidth: 300,
        valueGetter: (value) => {
          const model = models.find((model) => model.name === value);
          return model && model.display_name ? model.display_name : value;
        },
      },
      {
        field: "task_name",
        headerName: "Task",
        minWidth: 200,
        valueGetter: (value) => {
          const task = tasks.find((task) => task.name === value);
          return task && task.display_name ? task.display_name : value;
        },
      },
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
      const rowsFetched = await get_model_table();
      setRows(rowsFetched);
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
          Provide a prediction name
        </Typography>

        <PredictionNameInput
          defaultPredictionName={defaultPredictionName}
          onValidChange={setIsNameValid}
          onNameChange={onPredictNameInput}
        />
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Typography variant="subtitle1" component="h3" sx={{ mb: 3 }}>
          Select a model to use for prediction
        </Typography>
        <Paper
          sx={{
            height: 400,
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <DataGrid
            rows={rows}
            columns={columns}
            pageSize={5}
            rowsPerPageOptions={[5]}
            onRowClick={handleRowClick}
            density="compact"
            sx={{
              "& .MuiDataGrid-columnHeaders": {
                backgroundColor: "background.box",
                position: "sticky",
                top: 0,
                zIndex: 1,
              },
            }}
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
