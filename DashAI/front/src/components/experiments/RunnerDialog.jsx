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
import {
  checkQueueAndMaybeStartPolling,
  forceRefreshNow,
} from "../../utils/jobPoller";

/**
 * Modal for selecting the runs to be sent to execute in an experiment
 * @param {object} experiment contains the information of an experiment as received from the backend (IExperiment)
 */
function RunnerDialog({ experiment, expRunning, setExpRunning }) {
  const { enqueueSnackbar } = useSnackbar();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [finishedRunning, setFinishedRunning] = useState(false);
  const intervalRef = useRef(null);

  // Función mejorada que sigue más de cerca la implementación original
  const getRuns = async ({ showLoading = true } = {}) => {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const runs = await getRunsRequest(experiment.id.toString());

      // Buscar explícitamente un run con status "running" (2)
      const firstRunInExecution = runs.find((run) => run.status === 2);

      // Si hay un run ejecutándose, asegurarse de que expRunning refleje eso
      if (firstRunInExecution !== undefined) {
        // Modificar el estado solo si el valor cambia
        if (!expRunning[experiment.id]) {
          setExpRunning({ ...expRunning, [experiment.id]: true });
        }
      }

      // Transformar código de estado a texto
      const runsWithStringStatus = runs.map((run) => {
        return { ...run, status: getRunStatus(run.status) };
      });

      setRows(runsWithStringStatus);

      // Inicializar selección si es necesario
      if (rowSelectionModel.length === 0) {
        setRowSelectionModel(runs.map((run) => run.id));
      }

      // Verificar si todos los runs seleccionados han terminado
      if (expRunning[experiment.id]) {
        const selectedRuns = runs.filter((run) =>
          rowSelectionModel.includes(run.id),
        );

        const allRunsFinished =
          selectedRuns.length > 0 &&
          selectedRuns.every((run) => run.status === 3 || run.status === 4); // finished o error

        if (allRunsFinished) {
          setExpRunning({ ...expRunning, [experiment.id]: false });

          // Solo mostrar snackbar una vez
          if (!finishedRunning) {
            enqueueSnackbar(`${experiment.name} has completed all its runs`, {
              variant: "success",
            });
            setFinishedRunning(true);

            setTimeout(() => {
              forceRefreshNow();
            }, 300);

            setTimeout(() => {
              forceRefreshNow();
            }, 1000);
          }
        }
      }
    } catch (error) {
      enqueueSnackbar(
        `Error while trying to obtain the runs associated to ${experiment.name}`,
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

      return false; // retornar false para éxito
    } catch (error) {
      enqueueSnackbar(`Error while trying to enqueue run with id ${runId}`);
      console.error("Error enqueueing run:", error);
      return true; // retornar true para error
    }
  };

  const handleExecuteRuns = async () => {
    setExpRunning({ ...expRunning, [experiment.id]: true });
    setFinishedRunning(false);
    let enqueueErrors = 0;

    // Enviar runs al job queue
    for (const runId of rowSelectionModel) {
      const error = await enqueueRunnerJob(runId);
      enqueueErrors = error ? enqueueErrors + 1 : enqueueErrors;
    }

    // Verificar que al menos un job fue encolado con éxito
    if (enqueueErrors < rowSelectionModel.length) {
      // Obtener un update inmediato
      checkQueueAndMaybeStartPolling();
      setTimeout(() => {
        forceRefreshNow();
      }, 300);

      setTimeout(() => {
        getRuns({ showLoading: false });
      }, 100);
    } else {
      setExpRunning({ ...expRunning, [experiment.id]: false });
    }
  };

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

  // Al montar, obtener runs asociados al experimento
  useEffect(() => {
    getRuns();
  }, []);

  // Polling para actualizar el estado de los runs - ESTA ES LA PARTE CLAVE
  useEffect(() => {
    // Si el experimento está corriendo o el modal está abierto, hacer polling
    if (expRunning[experiment.id] || open) {
      // Obtener datos inicialmente
      const initialGetRuns = async () => {
        await getRuns({ showLoading: false });
      };

      initialGetRuns().then(() => {
        // Limpiar intervalo anterior
        clearInterval(intervalRef.current);

        // Iniciar polling
        intervalRef.current = setInterval(
          () => getRuns({ showLoading: false }),
          1000, // Poll cada segundo
        );
      });
    } else {
      clearInterval(intervalRef.current);
    }

    // Limpiar al desmontar
    return () => {
      clearInterval(intervalRef.current);
    };
  }, [expRunning[experiment.id], open]);

  return (
    <React.Fragment>
      <GridActionsCellItem
        key="runner-button"
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
        onClick={() => setOpen(true)}
      />
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth={"md"}
      >
        <DialogTitle>{`Runs in ${experiment.name}`}</DialogTitle>
        <DialogContent>
          <Paper
            sx={{ px: 3, py: 2 }}
            // Soluciona un problema de mui relacionado con poner datagrid dentro de otro datagrid
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
              variant="contained"
              loading={expRunning[experiment.id]}
              endIcon={finishedRunning ? <CheckIcon /> : <PlayArrowIcon />}
              onClick={
                finishedRunning ? () => setOpen(false) : handleExecuteRuns
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
