import React, { useEffect, useState } from "react";
import { DataGrid, GridActionsCellItem, GridToolbar } from "@mui/x-data-grid";
import { Grid, MenuItem, Paper, TextField, Typography } from "@mui/material";
import QueryStatsIcon from "@mui/icons-material/QueryStats";
import { useNavigate } from "react-router-dom";
import { useSnackbar } from "notistack";
import { getModelSessions as getModelSessionsRequest } from "../../api/modelSession";
import { getRuns as getRunsRequest } from "../../api/run";
import { formatDate } from "../../utils";
import { getComponents } from "../../api/component";
import TimestampWrapper from "../shared/TimestampWrapper";
import { TIMESTAMP_KEYS } from "../../constants/timestamp";
import { useTranslation } from "react-i18next";

function TrainedModelsTable() {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState("All Tasks");
  const [tasks, setTasks] = useState([]);
  const [originalRows, setOriginalRows] = useState([]);
  const [models, setModels] = useState([]);
  const { t } = useTranslation(["common"]);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await getComponents({ selectTypes: ["Model"] });
        setModels(response);
      } catch (error) {
        console.error("Error fetching models:", error);
      }
    };
    fetchModels();
  }, []);

  const colums = [
    {
      field: "id",
      headerName: t("common:id"),
      minWidth: 30,
      editable: false,
    },
    {
      field: "experimentName",
      headerName: t("common:experimentName"),
      minWidth: 170,
      editable: false,
    },
    {
      field: "name",
      headerName: t("common:modelName"),
      minWidth: 170,
      editable: false,
    },
    {
      field: "model_name",
      headerName: t("common:model"),
      minWidth: 170,
      editable: false,
      valueGetter: (value) => {
        const model = models.find((model) => model.name === value);
        return model && model.display_name ? model.display_name : value;
      },
    },
    {
      field: "created",
      headerName: t("common:created"),
      minWidth: 170,
      editable: false,
      type: Date,
      valueGetter: (value) => formatDate(value),
    },
    {
      field: "actions",
      headerName: t("common:dashboard"),
      headerWidth: 1,
      type: "actions",
      mindWidth: 170,
      getActions: (params) => [
        <TimestampWrapper
          key="enter-dashboard"
          eventName={TIMESTAMP_KEYS.explainer.enterDashboard}
        >
          <GridActionsCellItem
            key="specific-results-button"
            icon={<QueryStatsIcon />}
            label="Run Results"
            onClick={() =>
              navigate(`/app/explainers/runs/${params.row.id}`, {
                state: {
                  modelName: params.row.name,
                  taskName: params.row.taskName,
                },
              })
            }
            sx={{ color: "primary.main" }}
          />
        </TimestampWrapper>,
      ],
    },
  ];

  const extractRows = (rawExperiments, rawRuns) => {
    let rows = [];
    // A cada run agregarlo los datos de su model session
    rawRuns.forEach((run) => {
      let newRun = { ...run };
      const modelSession = rawExperiments.filter(
        (session) => session.id === newRun.model_session_id,
      )[0];

      if (!modelSession) {
        console.warn(`Model session not found for run ${newRun.id}`);
        return;
      }

      const {
        name: experimentName,
        dataset_id: datasetId,
        task_name: taskName,
      } = modelSession;
      newRun = {
        ...newRun,
        experimentName,
        datasetId,
        taskName,
      };
      rows = [...rows, newRun];
    });
    return rows;
  };

  const getModels = async () => {
    setLoading(true);
    try {
      const experiments = await getModelSessionsRequest();
      const runs = await getRunsRequest();
      const rows = extractRows(experiments, runs);
      const filteredRows = rows.filter((row) => row.status === 3);
      setOriginalRows(filteredRows);
      setRows(filteredRows);
    } catch (error) {
      enqueueSnackbar(t("explainers:error.fetchRuns"));
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

  const getTasks = async () => {
    setLoading(true);
    try {
      const tasks = await getComponents({ selectTypes: ["Task"] });
      setTasks(tasks);
    } catch (error) {
      enqueueSnackbar(t("explainers:error.fetchTasks"));
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
    getModels();
    getTasks();
  }, []);

  const taskFilter = (event) => {
    const taskName = event.target.value;
    setSelectedTask(taskName);
    if (taskName === "All Tasks") {
      setRows(originalRows);
    } else {
      let newRows = [];
      originalRows.forEach((row) => {
        if (row.taskName === taskName) {
          newRows = [...newRows, row];
        }
      });
      setRows(newRows);
    }
  };

  return (
    <Paper sx={{ py: 4, px: 6 }}>
      <Grid container spacing={2}>
        <Grid size={{ xs: 4 }}>
          <Typography variant="h6" component="h2" sx={{ mb: 1 }}>
            {t("common:models")}
          </Typography>
        </Grid>
        <Grid size={{ xs: 4 }}></Grid>
        <Grid size={{ xs: 4 }}>
          <TextField
            sx={{ mb: 1, mt: -1 }}
            select
            label={t("common:selectTask")}
            value={selectedTask}
            onChange={taskFilter}
            fullWidth
          >
            <MenuItem key={"Wildcard"} value={"All Tasks"}>
              {t("common:allTasks")}
            </MenuItem>
            {tasks.map((task) => (
              <MenuItem key={task.name} value={task.name}>
                {task.name}
              </MenuItem>
            ))}
          </TextField>
        </Grid>
      </Grid>
      <DataGrid
        rows={rows}
        columns={colums}
        initialState={{
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
        }}
        slots={{
          toolbar: GridToolbar,
        }}
        sortModel={[{ field: "experiment", sort: "desc" }]}
        columnVisibilityModel={{ id: false }}
        pageSize={5}
        pageSizeOptions={[5, 10]}
        disableRowSelectionOnClick
        autoHeight
        loading={loading}
      />
    </Paper>
  );
}

export default TrainedModelsTable;
