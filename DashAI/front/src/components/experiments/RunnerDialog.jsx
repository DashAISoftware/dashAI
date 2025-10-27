import React, { useState, useEffect, useCallback, useRef } from "react";
import PropTypes from "prop-types";
import {
  PlayArrow as PlayArrowIcon,
  Check as CheckIcon,
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
} from "@mui/material";
import { getRuns as getRunsRequest } from "../../api/run";
import { enqueueRunnerJob as enqueueRunnerJobRequest } from "../../api/job";
import { useSnackbar } from "notistack";
import { getRunStatus } from "../../utils/runStatus";
import { LoadingButton } from "@mui/lab";
import { startJobPolling } from "../../utils/jobPoller";
import { useTourContext } from "../tour/TourProvider";

function RunnerDialog({ experiment, expRunning, setExpRunning }) {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [finishedRunning, setFinishedRunning] = useState(false);
  const [trackedJobIds, setTrackedJobIds] = useState(new Set());
  const experimentNameRef = useRef(experiment.name);
  const tourContext = useTourContext();

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

    for (const runId of rowSelectionModel) {
      const error = await enqueueRunnerJob(runId);
      enqueueErrors = error ? enqueueErrors + 1 : enqueueErrors;
    }
    if (enqueueErrors < rowSelectionModel.length) {
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
    if (open || expRunning[experiment.id]) {
      const intervalId = setInterval(() => {
        getRuns({ showLoading: false });
      }, 2000);

      return () => clearInterval(intervalId);
    }
  }, [open, expRunning[experiment.id]]);

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
    },
    {
      field: "status",
      headerName: "Status",
      minWidth: 150,
      editable: false,
    },
  ];

  return (
    <React.Fragment>
      <GridActionsCellItem
        key="runner-button"
        data-tour="run-experiment-button"
        icon={
          expRunning[experiment.id] ? (
            <CircularProgress size={18} />
          ) : (
            <PlayArrowIcon />
          )
        }
        label="Run"
        disabled={
          !expRunning[experiment.id] &&
          Object.values(expRunning).some((value) => value === true)
        }
        onClick={handleOpenDialog}
      />
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth={"md"}
        data-tour="runner-dialog-progress"
      >
        <DialogTitle>{`Runs in ${experiment.name}`}</DialogTitle>
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
            <LoadingButton
              data-tour="runner-dialog-start"
              variant="contained"
              loading={expRunning[experiment.id]}
              endIcon={finishedRunning ? <CheckIcon /> : <PlayArrowIcon />}
              onClick={
                finishedRunning ? handleCloseAndAdvance : handleExecuteRuns
              }
            >
              {finishedRunning ? "Finished" : "Start"}
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
