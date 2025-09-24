import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";

import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
} from "@mui/icons-material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { Button, Grid, Paper, Typography, LinearProgress } from "@mui/material";
import { useSnackbar } from "notistack";

import { deleteExperiment as deleteExperimentRequest } from "../../api/experiment";
import { formatDate } from "../../utils";
import RunnerDialog from "./RunnerDialog";
import Results from "../../pages/results/Results";

import DeleteItemModal from "../custom/DeleteItemModal";

function ExperimentsTable({
  handleOpenNewExperimentModal,
  experiments = [],
  datasets = [],
  loading = false,
  onUpdateExperiments,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [expRunning, setExpRunning] = useState({});

  const deleteExperiment = async (id) => {
    try {
      await deleteExperimentRequest(id);
      enqueueSnackbar("Experiment successfully deleted.", {
        variant: "success",
      });
      onUpdateExperiments();
    } catch (error) {
      console.error(error);
      enqueueSnackbar("Error when trying to delete the experiment.");
    }
  };

  // Initialize running state when experiments change
  useEffect(() => {
    const initialRunningState = experiments.reduce((accumulator, current) => {
      return { ...accumulator, [current.id]: false };
    }, {});
    setExpRunning(initialRunningState);
  }, [experiments]);

  const handleDeleteExperiment = (id) => {
    deleteExperiment(id);
  };

  const columns = React.useMemo(
    () => [
      {
        field: "id",
        headerName: "ID",
        minWidth: 30,
        editable: false,
      },
      {
        field: "name",
        headerName: "Name",
        minWidth: 250,
        editable: false,
      },
      {
        field: "task_name",
        headerName: "Task",
        minWidth: 200,
        editable: false,
      },
      {
        field: "dataset_id",
        headerName: "Dataset",
        minWidth: 200,
        editable: false,
        valueFormatter: (params) => {
          const dataset = datasets.find((d) => d.id === params.value);
          return dataset ? dataset.name : `Dataset ID: ${params.value}`;
        },
      },
      {
        field: "created",
        headerName: "Created",
        minWidth: 140,
        editable: false,
        valueFormatter: (params) => formatDate(params.value),
      },
      {
        field: "last_modified",
        headerName: "Edited",
        type: Date,
        minWidth: 140,
        editable: false,
        valueFormatter: (params) => formatDate(params.value),
      },
      {
        field: "actions",
        type: "actions",
        minWidth: 180,
        getActions: (params) => [
          <RunnerDialog
            key="runner-dialog"
            experiment={params.row}
            expRunning={expRunning}
            setExpRunning={setExpRunning}
          />,
          <Results key="runs-dialog" experiment={params.row} />,
          <DeleteItemModal
            key="delete-button"
            deleteFromTable={() => handleDeleteExperiment(params.id)}
          />,
        ],
      },
    ],
    [handleDeleteExperiment, datasets],
  );

  return (
    <Paper sx={{ py: 4, px: 6 }}>
      {/* Title and new experiment button */}
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 4 }}
      >
        <Typography variant="h5" component="h2">
          Current experiments
        </Typography>
        <Grid item>
          <Grid container spacing={2}>
            <Grid item>
              <Button
                variant="contained"
                onClick={handleOpenNewExperimentModal}
                endIcon={<AddIcon />}
              >
                New Experiment
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="contained"
                onClick={onUpdateExperiments}
                endIcon={<UpdateIcon />}
              >
                Update
              </Button>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      {/* Experiments Table */}
      <DataGrid
        rows={experiments}
        columns={columns}
        initialState={{
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
        }}
        sortModel={[{ field: "id", sort: "desc" }]}
        columnVisibilityModel={{ id: false }}
        pageSizeOptions={[5, 10]}
        disableRowSelectionOnClick
        autoHeight
        loading={loading}
        slots={{
          toolbar: GridToolbar,
          loadingOverlay: LinearProgress,
        }}
      />
    </Paper>
  );
}

ExperimentsTable.propTypes = {
  handleOpenNewExperimentModal: PropTypes.func.isRequired,
  updateTableFlag: PropTypes.bool,
  setUpdateTableFlag: PropTypes.func,
  experiments: PropTypes.array,
  datasets: PropTypes.array,
  loading: PropTypes.bool,
  onUpdateExperiments: PropTypes.func.isRequired,
};

export default ExperimentsTable;
