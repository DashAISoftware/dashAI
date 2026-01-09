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
import { useTourContext } from "../tour/TourProvider";
import { getComponents } from "../../api/component";

import DeleteItemModal from "../custom/DeleteItemModal";
import { useTranslation } from "react-i18next";

function ExperimentsTable({
  handleOpenNewExperimentModal,
  experiments = [],
  datasets = [],
  loading = false,
  onUpdateExperiments,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [expRunning, setExpRunning] = useState({});
  const tourContext = useTourContext();
  const [tasks, setTasks] = useState([]);
  const { t } = useTranslation(["experiments", "common"]);

  const datasetMap = React.useMemo(() => {
    return new Map(datasets.map((dataset) => [dataset.id, dataset.name]));
  }, [datasets]);

  const deleteExperiment = async (id) => {
    try {
      await deleteExperimentRequest(id);
      enqueueSnackbar(t("experiments:message.runDeletedSuccessfully"), {
        variant: "success",
      });
      onUpdateExperiments();
    } catch (error) {
      console.error(error);
      enqueueSnackbar(t("experiments:error.errorDeletingRun"), {
        variant: "error",
      });
    }
  };

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const components = await getComponents({ selectTypes: ["Task"] });
        setTasks(components);
      } catch (error) {
        console.error("Error fetching tasks:", error);
      }
    };
    fetchTasks();
  }, []);

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

  const handleNewExperiment = () => {
    handleOpenNewExperimentModal();
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 300);
    }
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
        headerName: t("common:name"),
        minWidth: 250,
        editable: false,
      },
      {
        field: "task_name",
        headerName: t("common:task"),
        minWidth: 200,
        editable: false,
        valueGetter: (value) => {
          const task = tasks.find((task) => task.name === value);
          return task && task.display_name ? task.display_name : value;
        },
      },
      {
        field: "dataset_id",
        headerName: t("common:dataset"),
        minWidth: 200,
        editable: false,
        valueGetter: (value) => {
          const datasetName = datasetMap.get(value);
          return datasetName || `Dataset ID: ${value}`;
        },
      },
      {
        field: "created",
        headerName: t("common:created"),
        minWidth: 140,
        editable: false,
        valueGetter: (value) => formatDate(value),
      },
      {
        field: "last_modified",
        headerName: t("common:edited"),
        minWidth: 140,
        editable: false,
        valueGetter: (value) => formatDate(value),
      },
      {
        field: "actions",
        headerName: t("common:actions"),
        type: "actions",
        minWidth: 180,
        getActions: (params) => [
          // <RunnerDialog
          //   key="runner-dialog"
          //   experiment={params.row}
          //   expRunning={expRunning}
          //   setExpRunning={setExpRunning}
          //   deleteExperiment={() => handleDeleteExperiment(params.id)}
          // />,
          <Results
            key="runs-dialog"
            experiment={params.row}
            handleDeleteExperiment={handleDeleteExperiment}
          />,
          <DeleteItemModal
            key="delete-button"
            deleteFromTable={() => handleDeleteExperiment(params.id)}
          />,
        ],
      },
    ],
    [handleDeleteExperiment, datasetMap],
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
          {t("experiments:label.currentExperiments")}
        </Typography>
        <Grid>
          <Grid container spacing={2}>
            <Grid>
              <Button
                data-tour="new-experiment-button"
                variant="contained"
                onClick={handleNewExperiment}
                endIcon={<AddIcon />}
              >
                {t("experiments:button.newExperiment")}
              </Button>
            </Grid>
            <Grid>
              <Button
                variant="contained"
                onClick={onUpdateExperiments}
                endIcon={<UpdateIcon />}
              >
                {t("common:update")}
              </Button>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      {/* Experiments Table */}
      <DataGrid
        data-tour="experiments-table"
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
