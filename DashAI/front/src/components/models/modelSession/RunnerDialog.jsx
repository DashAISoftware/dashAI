import React, { useState, useEffect, useCallback, useRef } from "react";
import PropTypes from "prop-types";
import {
  PlayArrow as PlayArrowIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from "@mui/icons-material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
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
import { useTheme } from "@mui/material/styles";
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
import { useTranslation } from "react-i18next";

const toMRT = (ids) => Object.fromEntries(ids.map((id) => [String(id), true]));
const fromMRT = (sel) =>
  Object.keys(sel)
    .filter((k) => sel[k])
    .map(Number);

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
  const { t, i18n } = useTranslation(["experiments", "common"]);
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const hasActiveRuns = rows.some(
    (r) => r.status === 1 || r.status === 2, // Delivered or Started
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

      setRows(runs);

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
              t("experiments:message.experimentCompleted", {
                experimentName: experimentNameRef.current,
              }),
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
        t("experiments:error.errorFetchingRuns", {
          experimentName: experimentNameRef.current,
        }),
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
            enqueueSnackbar(
              t("experiments:error.runFailed", {
                error: result.error || "Unknown error",
              }),
              {
                variant: "error",
              },
            );
            getRuns({ showLoading: false });
          },
        );
      }

      return false;
    } catch (error) {
      enqueueSnackbar(
        t("experiments:error.errorEnqueueingRun", {
          runId,
        }),
        {
          variant: "error",
        },
      );
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
        run.status === 0 || // Not Started
        run.status === 4 || // Error
        run.status === 3 // Finished
      );
    });

    // If no runs to execute, show a message
    if (runsToExecute.length === 0) {
      enqueueSnackbar(t("experiments:message.noRunsToExecute"), {
        variant: "info",
      });
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
              t("experiments:error.runFailed", {
                error: result.error || "Unknown error",
              }),
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
      enqueueSnackbar(
        t("experiments:error.errorEnqueueingRun", {
          runId: run.id,
        }),
        {
          variant: "error",
        },
      );
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
      accessorKey: "name",
      header: t("common:name"),
      minSize: 250,
    },
    {
      accessorKey: "model_name",
      header: t("experiments:label.modelName"),
      minSize: 300,
      Cell: ({ cell }) => {
        const value = cell.getValue();
        const model = models.find((m) => m.name === value);
        return model && model.display_name ? model.display_name : value;
      },
    },
    {
      accessorKey: "status",
      header: t("common:status"),
      minSize: 150,
    },
    {
      id: "actions",
      header: t("common:actions"),
      minSize: 180,
      enableSorting: false,
      enableColumnFilter: false,
      Cell: ({ row }) => (
        <Box sx={{ display: "flex", gap: 0.5 }}>
          <SingleRun run={row.original} onRun={handleSingleRun} />
          <EditRunDialog
            experiment={experiment}
            run={row.original}
            setRun={(updatedRun) =>
              setRows((prev) =>
                prev.map((r) => (r.id === updatedRun.id ? updatedRun : r)),
              )
            }
          />
          <DeleteRun
            run={row.original}
            onRunDelete={() => {
              setRows((prevRows) =>
                prevRows.filter((r) => r.id !== row.original.id),
              );
              if (rows.length === 1) {
                setOpen(false);
                deleteExperiment();
              }
            }}
          />
        </Box>
      ),
    },
  ];

  const mrtRowSelection = toMRT(rowSelectionModel);

  const table = useMaterialReactTable({
    columns,
    data: rows,
    state: {
      isLoading: loading,
      rowSelection: mrtRowSelection,
    },
    getRowId: (row) => String(row.id),
    enableRowSelection: true,
    onRowSelectionChange: (updater) => {
      const next =
        typeof updater === "function" ? updater(mrtRowSelection) : updater;
      setRowSelectionModel(fromMRT(next));
    },
    enablePagination: true,
    initialState: {
      pagination: { pageSize: 5, pageIndex: 0 },
    },
    localization,
    enableFullScreenToggle: false,
    enableDensityToggle: false,
  });

  return (
    <React.Fragment>
      <IconButton
        key="runner-button"
        data-tour="run-experiment-button"
        onClick={handleOpenDialog}
        size="small"
      >
        {rows.some(
          (row) => row.status === 1 || row.status === 2, // Delivered or Started
        ) ? (
          <CircularProgress size={18} />
        ) : (
          <PlayArrowIcon />
        )}
      </IconButton>
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
            <MaterialReactTable table={table} />
          </Paper>
        </DialogContent>
        <DialogActions>
          <ButtonGroup size="large" sx={{ justifyContent: "flex-end", p: 2 }}>
            <Button
              variant="outlined"
              onClick={handleCloseAndAdvance}
              data-tour="runner-dialog-close"
            >
              {t("common:close")}
            </Button>
            <LoadingButton
              data-tour="runner-dialog-start"
              variant="contained"
              loading={rows.every(
                (row) => row.status === 1 || row.status === 2, // Delivered or Started
              )}
              endIcon={<PlayArrowIcon />}
              onClick={handleExecuteRuns}
            >
              {t("experiments:button.runAll")}
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
