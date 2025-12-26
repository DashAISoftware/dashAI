import React, { useState, useEffect, useCallback, useRef } from "react";
import PropTypes from "prop-types";
import {
  PlayArrow as PlayArrowIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from "@mui/icons-material";
import { DataGrid, GridActionsCellItem } from "@mui/x-data-grid";
import {
  Box,
  ButtonGroup,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Typography,
  IconButton,
  Button,
} from "@mui/material";
import { getRuns as getRunsRequest } from "../../api/run";
import { enqueueRunnerJob as enqueueRunnerJobRequest } from "../../api/job";
import { useSnackbar } from "notistack";
import { getRunStatus } from "../../utils/runStatus";
import { LoadingButton } from "@mui/lab";
import { startJobPolling } from "../../utils/jobPoller";
import { useTourContext } from "../tour/TourProvider";
import { getComponents } from "../../api/component";
import SingleRun from "./runButtons/SingleRun";
import EditRunDialog from "./runButtons/EditRunDialog";
import DeleteRun from "./runButtons/DeleteRun";

function RunnerDialog({
  experiment,
  expRunning,
  setExpRunning,
  deleteExperiment,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [finishedRunning, setFinishedRunning] = useState(false);
  const [trackedJobIds, setTrackedJobIds] = useState(new Set());
  const experimentNameRef = useRef(experiment.name);
  const tourContext = useTourContext();
  const [models, setModels] = useState([]);

  const hasActiveRuns = rows.some(
    (r) => r.status === "Delivered" || r.status === "Started",
  );

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

  // Update ref when experiment name changes
  useEffect(() => {
    experimentNameRef.current = experiment.name;
  }, [experiment.name]);

  const getRuns = async ({ showLoading = true } = {}) => {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const runs = await getRunsRequest(experiment.id.toString());

      // Check for any running runs
      const runningRun = runs.find((run) => run.status === 2);
      if (runningRun && !expRunning[experiment.id]) {
        setExpRunning({ ...expRunning, [experiment.id]: true });
      }

      // Transform status codes to text
      const runsWithStringStatus = runs.map((run) => ({
        ...run,
        status: getRunStatus(run.status),
      }));

      setRows(runsWithStringStatus);

      // Initialize selection if needed
      if (rowSelectionModel.length === 0) {
        setRowSelectionModel(runs.map((run) => run.id));
      }

      // Check if all selected runs are finished
      if (expRunning[experiment.id]) {
        const selectedRuns = runs.filter((run) =>
          rowSelectionModel.includes(run.id),
        );

        const allRunsFinished =
          selectedRuns.length > 0 &&
          selectedRuns.every((run) => run.status === 3 || run.status === 4);

        if (allRunsFinished) {
          setExpRunning({ ...expRunning, [experiment.id]: false });

          if (!finishedRunning) {
            enqueueSnackbar(
              `${experimentNameRef.current} has completed all runs`,
              {
                variant: "success",
              },
            );
            setFinishedRunning(true);
          }
        }
      }
    } catch (error) {
      enqueueSnackbar(
        `Error retrieving runs for ${experimentNameRef.current}`,
        { variant: "error" },
      );
      console.error("Error fetching runs:", error);
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  const enqueueRunnerJob = async (runId) => {
    try {
      const response = await enqueueRunnerJobRequest(runId);

      if (response && response.id) {
        setTrackedJobIds((prev) => new Set(prev).add(response.id));

        startJobPolling(
          response.id,
          (result) => {
            getRuns({ showLoading: false });
          },
          (result) => {
            console.error(`Run job ${response.id} failed:`, result);
            enqueueSnackbar(`Run failed: ${result.error || "Unknown error"}`, {
              variant: "error",
            });
            getRuns({ showLoading: false });
          },
        );
      }

      return false;
    } catch (error) {
      enqueueSnackbar(`Error enqueueing run with ID ${runId}`, {
        variant: "error",
      });
      console.error("Error enqueueing run:", error);
      return true;
    }
  };

  const handleExecuteRuns = async () => {
    setExpRunning({ ...expRunning, [experiment.id]: true });
    setFinishedRunning(false);
    let enqueueErrors = 0;

    // Filter runs to only include those that are not started or have "Delivered" status
    const runsToExecute = rowSelectionModel.filter((runId) => {
      const run = rows.find((r) => r.id === runId);
      // Only execute if status is not started or delivered
      return (
        !run ||
        !run.status ||
        run.status === "Not Started" ||
        run.status === "Error" ||
        run.status === "Finished"
      );
    });

    // If no runs to execute, show a message
    if (runsToExecute.length === 0) {
      enqueueSnackbar(
        "No runs available to execute. Selected runs may already be running or completed.",
        {
          variant: "info",
        },
      );
      setExpRunning({ ...expRunning, [experiment.id]: false });
      return;
    }

    // Optimistically update all runs to "Started" status
    setRows((prevRows) =>
      prevRows.map((row) =>
        runsToExecute.includes(row.id) ? { ...row, status: "Started" } : row,
      ),
    );

    for (const runId of runsToExecute) {
      const error = await enqueueRunnerJob(runId);
      enqueueErrors = error ? enqueueErrors + 1 : enqueueErrors;
    }

    if (enqueueErrors < runsToExecute.length) {
      setTimeout(() => {
        getRuns({ showLoading: false });
      }, 100);

      if (tourContext && tourContext.run) {
        setTimeout(() => {
          tourContext.nextStep();
        }, 1000);
      }
    } else {
      setExpRunning({ ...expRunning, [experiment.id]: false });
      getRuns({ showLoading: false });
    }
  };

  const handleSingleRun = async (run) => {
    try {
      setRows((prevRows) =>
        prevRows.map((row) =>
          row.id === run.id ? { ...row, status: "Started" } : row,
        ),
      );

      const response = await enqueueRunnerJobRequest(run.id);

      if (response && response.id) {
        enqueueSnackbar(`Run ${run.name} started successfully`, {
          variant: "success",
        });

        setTrackedJobIds((prev) => new Set(prev).add(response.id));

        startJobPolling(
          response.id,
          (result) => {
            getRuns({ showLoading: false });
          },
          (result) => {
            console.error(`Run job ${response.id} failed:`, result);
            enqueueSnackbar(
              `Run ${run.name} failed: ${result.error || "Unknown error"}`,
              {
                variant: "error",
              },
            );
            getRuns({ showLoading: false });
          },
        );
      }
    } catch (error) {
      console.error("Error enqueueing run:", error);
      enqueueSnackbar(`Error starting run ${run.name}`, {
        variant: "error",
      });
      getRuns({ showLoading: false });
    }
  };

  const handleCloseAndAdvance = () => {
    setOpen(false);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 600);
    }
  };

  const handleOpenDialog = () => {
    setOpen(true);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };

  useEffect(() => {
    getRuns();
  }, []);

  useEffect(() => {
    if (hasActiveRuns) {
      const intervalId = setInterval(() => {
        getRuns({ showLoading: false });
      }, 2000);

      return () => clearInterval(intervalId);
    }
  }, [hasActiveRuns]);

  const columns = [
    {
      field: "name",
      headerName: "Name",
      minWidth: 250,
      editable: false,
    },
    {
      field: "model_name",
      headerName: "Model Name",
      minWidth: 300,
      editable: false,
      valueGetter: (value) => {
        const model = models.find((model) => model.name === value);
        return model && model.display_name ? model.display_name : value;
      },
    },
    {
      field: "status",
      headerName: "Status",
      minWidth: 150,
      editable: false,
    },
    {
      field: "actions",
      headerName: "Actions",
      type: "actions",
      minWidth: 180,
      getActions: (params) => [
        <SingleRun key="single-run" run={params.row} onRun={handleSingleRun} />,
        <EditRunDialog
          key="edit-run-dialog"
          experiment={experiment}
          run={params.row}
          setRun={(updatedRun) =>
            setRows((prev) =>
              prev.map((r) => (r.id === updatedRun.id ? updatedRun : r)),
            )
          }
        />,
        <DeleteRun
          key="delete-run-dialog"
          run={params.row}
          onRunDelete={() => {
            setRows((prevRows) =>
              prevRows.filter((row) => row.id !== params.row.id),
            );
            if (rows.length === 1) {
              setOpen(false);
              deleteExperiment();
            }
          }}
        />,
      ],
    },
  ];

  return (
    <React.Fragment>
      <GridActionsCellItem
        key="runner-button"
        data-tour="run-experiment-button"
        icon={
          rows.some(
            (row) => row.status === "Delivered" || row.status === "Started",
          ) ? (
            <CircularProgress size={18} />
          ) : (
            <PlayArrowIcon />
          )
        }
        label="Run"
        onClick={handleOpenDialog}
      />
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth={"lg"}
        data-tour="runner-dialog-progress"
      >
        <DialogTitle>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            {`Runs in ${experiment.name}`}
            <IconButton
              onClick={() => setOpen(false)}
              sx={{
                color: (theme) => theme.palette.grey[500],
              }}
            >
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Paper
            sx={{ px: 3, py: 2 }}
            onClick={(event) => {
              event.target = document.body;
            }}
          >
            <Typography variant="subtitle1" component="h3" sx={{ pb: 1 }}>
              Select models to run
            </Typography>
            <DataGrid
              rows={rows}
              columns={columns}
              checkboxSelection
              onRowSelectionModelChange={(newRowSelectionModel) => {
                setRowSelectionModel(newRowSelectionModel);
              }}
              rowSelectionModel={rowSelectionModel}
              initialState={{
                pagination: {
                  paginationModel: {
                    pageSize: 5,
                  },
                },
              }}
              pageSizeOptions={[5]}
              disableRowSelectionOnClick
              autoHeight
              loading={loading}
            />
          </Paper>
        </DialogContent>
        <DialogActions>
          <ButtonGroup size="large" sx={{ justifyContent: "flex-end", p: 2 }}>
            <Button
              variant="outlined"
              onClick={handleCloseAndAdvance}
              data-tour="runner-dialog-close"
            >
              Close
            </Button>
            <LoadingButton
              data-tour="runner-dialog-start"
              variant="contained"
              loading={rows.every(
                (row) => row.status === "Delivered" || row.status === "Started",
              )}
              endIcon={<PlayArrowIcon />}
              onClick={handleExecuteRuns}
            >
              Run all
            </LoadingButton>
          </ButtonGroup>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}

RunnerDialog.propTypes = {
  experiment: PropTypes.shape({
    name: PropTypes.string,
    id: PropTypes.number,
  }).isRequired,
  expRunning: PropTypes.objectOf(PropTypes.bool).isRequired,
  setExpRunning: PropTypes.func.isRequired,
};

export default RunnerDialog;
