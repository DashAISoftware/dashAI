import React, { useState, useEffect, useRef } from "react";
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
import {
  getRuns as getRunsRequest,
  getRunById,
  resetRunById,
} from "../../../api/run";
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
  const hasNotifiedRef = useRef(false);
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

      if (allRunsFinished && !hasNotifiedRef.current) {
        hasNotifiedRef.current = true;

        enqueueSnackbar(`${experiment.name} has completed all runs`, {
          variant: "success",
        });

        setFinishedRunning(true);

        if (tourContext && tourContext.run) {
          tourContext.nextStep();
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
    hasNotifiedRef.current = false;
    if (tourContext && tourContext.run) {
      tourContext.nextStep();
    }

    const runsToExecute = rowSelectionModel.filter((runId) => {
      const run = runs.find((r) => r.id === runId);
      return (
        !run ||
        !run.status ||
        run.status === "Not Started" ||
        run.status === "Error" ||
        run.status === "Finished"
      );
    });

    if (runsToExecute.length === 0) {
      enqueueSnackbar(
        "No runs available to execute. Selected runs may already be running or completed.",
        { variant: "info" },
      );
      return;
    }

    try {
      const updatedRuns = await Promise.all(
        runsToExecute.map((runId) => resetRunById(runId)),
      );
      let enqueueErrors = 0;
      for (const runId of runsToExecute) {
        const error = await enqueueRunnerJob(runId);
        if (error) enqueueErrors++;
      }

      setRuns((prevRuns) =>
        prevRuns.map((r) => {
          const updated = updatedRuns.find((u) => u.id === r.id);
          return updated ? { ...updated, status: "Delivered" } : r;
        }),
      );

      if (enqueueErrors < runsToExecute.length) {
        enqueueSnackbar(
          `${runsToExecute.length - enqueueErrors} run(s) started successfully`,
          { variant: "success" },
        );
      } else {
        getRuns({ showLoading: false });
      }
    } catch (error) {
      console.error("Error executing runs:", error);
      enqueueSnackbar("Error executing runs", { variant: "error" });

      getRuns({ showLoading: false });
    }
  };

  const handleSingleRun = async (run) => {
    try {
      hasNotifiedRef.current = false;
      // Immediately reset the run state before enqueueing
      const initialUpdatedRun = await resetRunById(run.id);

      // Enqueue the run
      const response = await enqueueRunnerJobRequest(run.id);

      if (!response || !response.id) {
        enqueueSnackbar(`Error starting run ${run.id}`, {
          variant: "error",
        });
        return;
      }

      // Update run to "Delivered" status
      initialUpdatedRun.status = 1;
      enqueueSnackbar(`Run ${run.id} started successfully`, {
        variant: "success",
      });

      // Track job ID
      setTrackedJobIds((prev) => new Set(prev).add(response.id));

      setRuns((prevRuns) =>
        prevRuns.map((r) =>
          r.id === run.id
            ? {
                ...initialUpdatedRun,
                status: getRunStatus(initialUpdatedRun.status),
              }
            : r,
        ),
      );

      // Start polling only this run
      startJobPolling(
        response.id,
        async () => {
          // Job completed, fetch only this run
          const updated = await getRunById(run.id);

          setRuns((prevRuns) =>
            prevRuns.map((r) =>
              r.id === run.id
                ? {
                    ...updated,
                    status: getRunStatus(updated.status),
                  }
                : r,
            ),
          );
        },
        async (result) => {
          // Job failed, still fetch only this run
          enqueueSnackbar(
            `Run ${run.id} failed: ${result.error || "Unknown error"}`,
            { variant: "error" },
          );

          const updated = await getRunById(run.id);

          setRuns((prevRuns) =>
            prevRuns.map((r) =>
              r.id === run.id
                ? {
                    ...updated,
                    status: getRunStatus(updated.status),
                  }
                : r,
            ),
          );
        },
      );
    } catch (error) {
      console.error("Error enqueueing run:", error);

      enqueueSnackbar(`Error starting run ${run.id}`, {
        variant: "error",
      });

      // Fetch only the affected run to restore its real status
      const updated = await getRunById(run.id);

      setRuns((prevRuns) =>
        prevRuns.map((r) =>
          r.id === run.id
            ? {
                ...updated,
                status: getRunStatus(updated.status),
              }
            : r,
        ),
      );
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
            {!showTable ? <ResultsGraphs runs={runs} /> : null}
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
