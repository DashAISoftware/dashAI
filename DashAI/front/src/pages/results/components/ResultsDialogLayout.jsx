import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  Box,
  ButtonGroup,
} from "@mui/material";
import { Close, PlayArrow } from "@mui/icons-material";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import CustomLayout from "../../../components/custom/CustomLayout";
import ResultsDialogViews from "./ResultsDialogViews";
import ResultsTable from "./ResultsTable";
import ResultsGraphs from "./ResultsGraphs";
import { TIMESTAMP_KEYS } from "../../../constants/timestamp";
import { useTimestamp } from "../../../hooks/useTimestamp";
import { enqueueRunnerJob as enqueueRunnerJobRequest } from "../../../api/job";
import { useSnackbar } from "notistack";
import { getRunStatus } from "../../../utils/runStatus";
import { getRuns as getRunsRequest } from "../../../api/run";
import { startJobPolling } from "../../../utils/jobPoller";
import { LoadingButton } from "@mui/lab";
import { useTourContext } from "../../../components/tour/TourProvider";
import { deleteRun } from "../../../api/run";
import DeleteConfirmationModal from "../../../components/threeSectionLayout/DeleteConfirmationModal";

function ResultsDialogLayout({
  experiment,
  open,
  onClose,
  showTable,
  handleShowTable,
  handleShowGraphs,
  handleDeleteExperiment,
}) {
  const theme = useTheme();
  const screenSm = useMediaQuery(theme.breakpoints.down("sm"));
  const { handleClick } = useTimestamp({
    eventName: TIMESTAMP_KEYS.experiments.leavingResults,
  });

  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);
  const [trackedJobIds, setTrackedJobIds] = useState(new Set());
  const [finishedRunning, setFinishedRunning] = useState(false);
  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [runToDelete, setRunToDelete] = useState(null);
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();

  const hasActiveRuns = runs.some(
    (r) => r.status === "Delivered" || r.status === "Started",
  );

  const getRuns = async ({ showLoading = true } = {}) => {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const fetchedRuns = await getRunsRequest(experiment.id.toString());

      // Transform status codes to text
      const runsWithStringStatus = fetchedRuns.map((run) => ({
        ...run,
        status: getRunStatus(run.status),
      }));

      setRuns(runsWithStringStatus);

      // Initialize selection if needed
      if (rowSelectionModel.length === 0) {
        setRowSelectionModel(fetchedRuns.map((run) => run.id));
      }

      // Check if all selected runs are finished
      const selectedRuns = fetchedRuns.filter((run) =>
        rowSelectionModel.includes(run.id),
      );

      const allRunsFinished =
        selectedRuns.length > 0 &&
        selectedRuns.every((run) => run.status === 3 || run.status === 4);

      if (allRunsFinished) {
        if (!finishedRunning) {
          enqueueSnackbar(`${experiment.name} has completed all runs`, {
            variant: "success",
          });
          setFinishedRunning(true);
        }
      }
    } catch (error) {
      enqueueSnackbar(`Error retrieving runs for ${experiment.name}`, {
        variant: "error",
      });
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
    setFinishedRunning(false);
    let enqueueErrors = 0;

    // Filter runs to only include those that are not started or have "Delivered" status
    const runsToExecute = rowSelectionModel.filter((runId) => {
      const run = runs.find((r) => r.id === runId);
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
      return;
    }

    // Optimistically update all runs to "Started" status
    setRuns((prevRuns) =>
      prevRuns.map((run) =>
        runsToExecute.includes(run.id) ? { ...run, status: "Started" } : run,
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

      // if (tourContext && tourContext.run) {
      //   setTimeout(() => {
      //     tourContext.nextStep();
      //   }, 1000);
      // }
    } else {
      // Refresh to get actual status if all failed
      getRuns({ showLoading: false });
    }
  };

  const handleSingleRun = async (run) => {
    try {
      // Optimistically update to "Delivered"
      setRuns((prevRuns) =>
        prevRuns.map((r) =>
          r.id === run.id ? { ...r, status: "Delivered" } : r,
        ),
      );

      const response = await enqueueRunnerJobRequest(run.id);
      if (response && response.id) {
        enqueueSnackbar(`Run ${run.id} started successfully`, {
          variant: "success",
        });

        setTrackedJobIds((prev) => new Set(prev).add(response.id));

        // Start polling the job to track its progress
        startJobPolling(
          response.id,
          (result) => {
            // On success, refresh will happen from parent's polling
            console.log(`Run job ${response.id} completed successfully`);
            getRuns({ showLoading: false });
          },
          (result) => {
            // On failure
            console.error(`Run job ${response.id} failed:`, result);
            enqueueSnackbar(
              `Run ${run.id} failed: ${result.error || "Unknown error"}`,
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
      enqueueSnackbar(`Error starting run ${runId}`, {
        variant: "error",
      });
      // Revert the status on error by refreshing
      getRuns({ showLoading: false });
    }
  };

  const handleDeleteRun = async (run) => {
    setRunToDelete(run.id);
    setOpenDeleteModal(true);
  };

  const handleOnClose = () => {
    handleClick();
    onClose();
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

  return (
    <Dialog
      open={open}
      fullScreen={screenSm}
      fullWidth
      maxWidth={"lg"}
      onClose={handleOnClose}
      slotProps={{
        paper: {
          sx: {
            minHeight: "90vh",
            overflow: "auto",
            maxHeight: "90vh",
          },
        },
      }}
    >
      <DialogTitle>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {`Experiment ${experiment.name} results`}
          <IconButton
            onClick={handleOnClose}
            sx={{
              color: (theme) => theme.palette.grey[500],
            }}
          >
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>
      <Divider />
      <ResultsDialogViews
        showTable={showTable}
        handleShowTable={handleShowTable}
        handleShowGraphs={handleShowGraphs}
      />
      <Divider />
      {openDeleteModal && (
        <DeleteConfirmationModal
          open={openDeleteModal}
          onClose={() => {
            setOpenDeleteModal(false);
            setRunToDelete(null);
          }}
          onConfirm={async () => {
            try {
              setRuns((prevRuns) =>
                prevRuns.filter((run) => run.id !== runToDelete),
              );
              if (runs.length === 1) {
                handleDeleteExperiment(experiment.id);
              } else {
                await deleteRun(runToDelete);
              }
              enqueueSnackbar("Run deleted successfully", {
                variant: "success",
              });
            } catch (error) {
              console.error("Error deleting run:", error);
              enqueueSnackbar("Error deleting run", { variant: "error" });
            } finally {
              setOpenDeleteModal(false);
              setRunToDelete(null);
            }
          }}
          content="Are you sure you want to delete this run? This action cannot be undone."
        />
      )}

      {experiment && runs && (
        <Grid
          size={{ xs: 10 }}
          sx={{ width: "100%" }}
          data-tour="exp-results-metrics"
        >
          <CustomLayout>
            {showTable ? (
              <ResultsTable
                experiment={experiment}
                runs={runs}
                handleRun={handleSingleRun}
                handleDeleteRun={handleDeleteRun}
                handleExecuteRuns={handleExecuteRuns}
              />
            ) : null}
            {!showTable ? (
              <ResultsGraphs experimentId={experiment.id.toString()} />
            ) : null}
          </CustomLayout>
        </Grid>
      )}
    </Dialog>
  );
}

ResultsDialogLayout.propTypes = {
  experiment: PropTypes.shape({
    name: PropTypes.string,
    id: PropTypes.number,
  }).isRequired,
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  showTable: PropTypes.bool.isRequired,
  handleShowTable: PropTypes.func.isRequired,
  handleShowGraphs: PropTypes.func.isRequired,
};

export default ResultsDialogLayout;
