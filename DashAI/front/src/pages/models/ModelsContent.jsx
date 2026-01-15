import { useState, useEffect, useRef, useCallback } from "react";
import { Box, IconButton } from "@mui/material";
import { ChevronLeft, ChevronRight } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useLocation, useNavigate } from "react-router-dom";
import LeftBar from "../../components/models/LeftBar";
import CenterBox from "../../components/threeSectionLayout/CenterBox";
import RightBar from "../../components/models/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import CreateSessionSteps from "../../components/models/CreateSessionSteps";
import SessionVisualization from "../../components/models/SessionVisualization";
import DatasetVisualization from "../../components/DatasetVisualization";
import AddModelDialog from "../../components/models/AddModelDialog";
import RetrainConfirmDialog from "../../components/models/RetrainConfirmDialog";
import { getComponents } from "../../api/component";
import {
  getDatasets,
  getDatasetInfo,
  updateDataset,
  deleteDataset,
} from "../../api/datasets";
import {
  getExperiments,
  updateExperiment,
  deleteExperiment,
} from "../../api/experiment";
import {
  getRuns,
  deleteRun,
  resetRunById,
  getRunById,
  getRunOperationsCount,
  deleteRunOperations,
} from "../../api/run";
import { enqueueRunnerJob as enqueueRunnerJobRequest } from "../../api/job";
import { startJobPolling } from "../../utils/jobPoller";
import { getRunStatus } from "../../utils/runStatus";
import { useTranslation } from "react-i18next";

export default function ModelsContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [leftBarVisible, setLeftBarVisible] = useState(true);
  const [rightBarVisible, setRightBarVisible] = useState(true);
  const [leftBarWidth, setLeftBarWidth] = useState(20);
  const [rightBarWidth, setRightBarWidth] = useState(20);
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [runs, setRuns] = useState([]);
  const [addModelDialogOpen, setAddModelDialogOpen] = useState(false);
  const [preselectedModel, setPreselectedModel] = useState(null);

  const [retrainDialogOpen, setRetrainDialogOpen] = useState(false);
  const [runToRetrain, setRunToRetrain] = useState(null);
  const [operationsCount, setOperationsCount] = useState(null);

  const isResizingLeft = useRef(false);
  const isResizingRight = useRef(false);
  const [isTogglingLeft, setIsTogglingLeft] = useState(false);
  const [isTogglingRight, setIsTogglingRight] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "datasets", "common"]);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const data = await getComponents({
          selectTypes: ["Task"],
          hasRelatedOfType: "Model",
        });
        setTasks(data);
      } catch (error) {
        enqueueSnackbar(t("models:error.failedToFetchTasks"), {
          variant: "error",
        });
        console.error("Failed to fetch tasks:", error);
      }
    };
    fetchTasks();
  }, [enqueueSnackbar]);

  const enrichDatasetsWithInfo = async (newDatasets, existingDatasets = []) => {
    const enrichedDatasets = await Promise.all(
      newDatasets.map(async (dataset) => {
        const existingDataset = existingDatasets.find(
          (d) => d.id === dataset.id,
        );
        if (
          existingDataset &&
          existingDataset.total_rows !== undefined &&
          existingDataset.total_columns !== undefined
        ) {
          return {
            ...dataset,
            total_rows: existingDataset.total_rows,
            total_columns: existingDataset.total_columns,
          };
        }

        try {
          const info = await getDatasetInfo(dataset.id);
          return {
            ...dataset,
            total_rows: info.total_rows,
            total_columns: info.total_columns,
          };
        } catch (error) {
          console.warn(
            `Failed to fetch info for dataset ${dataset.id}:`,
            error,
          );
          return {
            ...dataset,
            description: dataset.description || "",
          };
        }
      }),
    );
    return enrichedDatasets;
  };

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const data = await getDatasets();
        const enrichedData = await enrichDatasetsWithInfo(data, []);
        setDatasets(enrichedData);
      } catch (error) {
        enqueueSnackbar(t("datasets:error.failedToFetchDatasets"), {
          variant: "error",
        });
        console.error("Failed to fetch datasets:", error);
      }
    };
    fetchDatasets();
  }, []);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await getExperiments();
        setSessions(data);
      } catch (error) {
        enqueueSnackbar(t("models:error.failedToFetchSessions"), {
          variant: "error",
        });
        console.error("Failed to fetch sessions:", error);
      }
    };
    fetchSessions();
  }, []);

  useEffect(() => {
    if (location.state?.openSessionId && sessions.length > 0) {
      const sessionToOpen = sessions.find(
        (s) => s.id === location.state.openSessionId,
      );
      if (sessionToOpen) {
        setSelectedSessionId(sessionToOpen.id);
        setSelectedSession(sessionToOpen);
        setStep(2);
        window.history.replaceState({}, document.title);
      }
    }
  }, [location.state, sessions]);

  const fetchRuns = useCallback(async () => {
    if (!selectedSessionId) return;
    try {
      const data = await getRuns(selectedSessionId.toString());
      const runsWithStatus = data.map((run) => ({
        ...run,
        status:
          typeof run.status === "number"
            ? run.status
            : getRunStatus(run.status),
      }));
      setRuns(runsWithStatus);
    } catch (error) {
      if (error.response?.status !== 404) {
        enqueueSnackbar(t("models:error.failedToFetchRuns"), {
          variant: "error",
        });
        console.error("Failed to fetch runs:", error);
      } else {
        setRuns([]);
      }
    }
  }, [selectedSessionId, enqueueSnackbar]);

  // Fetch runs when session is selected
  useEffect(() => {
    if (selectedSessionId) {
      fetchRuns();
    } else {
      setRuns([]);
      setSelectedSession(null);
    }
  }, [selectedSessionId, fetchRuns]);

  // Update selected session object when sessions or selectedSessionId changes
  useEffect(() => {
    if (selectedSessionId && sessions.length > 0) {
      const session = sessions.find((s) => s.id === selectedSessionId);
      setSelectedSession(session || null);
    }
  }, [selectedSessionId, sessions]);

  const handleTaskSelect = (taskName) => {
    const task = tasks.find((t) => t.name === taskName);
    setSelectedTask(task);
    setStep(1);
  };

  const handleBackToTaskSelection = () => {
    setSelectedTask(null);
    setStep(0);
  };

  const handleSessionCreated = (newSession) => {
    setSessions((prev) => [...prev, newSession]);
    setSelectedSessionId(newSession.id);
  };

  const handleSessionClick = (sessionId) => {
    setSelectedSessionId(sessionId);
  };

  const handleDatasetClick = (datasetId) => {
    setSelectedDatasetId(datasetId);
    setSelectedSessionId(null);
    setSelectedTask(null);
    setStep(2); // Use a different step to show DatasetVisualization
  };

  const handleSessionDelete = async (sessionId) => {
    if (sessionId === selectedSessionId) {
      setSelectedSessionId(null);
      setSelectedSession(null);
      setStep(0);
      setSelectedTask(null);
    }

    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== sessionId),
    );

    try {
      await deleteExperiment(sessionId.toString());
      enqueueSnackbar(t("models:message.sessionDeleted"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to delete session:", error);
      enqueueSnackbar(t("models:error.failedToDeleteSession"), {
        variant: "error",
      });
    }
  };

  const handleDatasetEdit = async (id, newName) => {
    try {
      const updatedDataset = await updateDataset(id, { name: newName });
      setDatasets((prevDatasets) =>
        prevDatasets.map((dataset) =>
          dataset.id === id
            ? { ...dataset, name: updatedDataset.name }
            : dataset,
        ),
      );
      enqueueSnackbar(t("datasets:message.datasetUpdateSuccess"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update dataset:", error);
      if (error.response?.status === 409) {
        enqueueSnackbar(t("datasets:error.datasetNameExists"), {
          variant: "error",
        });
      } else if (error.response?.status === 422) {
        enqueueSnackbar(t("datasets:error.datasetNameEmpty"), {
          variant: "error",
        });
      } else {
        enqueueSnackbar(t("datasets:error.failedToUpdateDataset"), {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const handleDatasetDelete = (id) => {
    if (id === selectedDatasetId) {
      setSelectedDatasetId(null);
      setStep(0);
      setSelectedTask(null);
    }

    setDatasets((prevDatasets) =>
      prevDatasets.filter((dataset) => dataset.id !== id),
    );

    setSessions((prevSessions) => {
      const filteredSessions = prevSessions.filter(
        (session) => session.dataset_id !== id,
      );

      if (
        selectedSessionId &&
        prevSessions.find(
          (session) =>
            session.id === selectedSessionId && session.dataset_id === id,
        )
      ) {
        setSelectedSessionId(null);
        setStep(0);
        setSelectedTask(null);
      }

      return filteredSessions;
    });

    deleteDataset(id);
  };

  const handleModelClick = (model) => {
    if (!selectedSession) {
      enqueueSnackbar(t("models:error.selectSessionFirst"), {
        variant: "warning",
      });
      return;
    }
    setPreselectedModel(model.name);
    setAddModelDialogOpen(true);
  };

  const handleRunCreated = (newRun) => {
    setRuns((prev) => [...prev, newRun]);
    enqueueSnackbar(t("models:message.runAdded", { runName: newRun.name }), {
      variant: "success",
    });
  };

  const handleTrainRun = async (run) => {
    try {
      // Check if run has been trained before (has metrics)
      const hasBeenTrained =
        run.test_metrics ||
        run.train_metrics ||
        run.validation_metrics ||
        getRunStatus(run.status) === "Finished";

      if (hasBeenTrained) {
        // Check for existing operations
        const opsCount = await getRunOperationsCount(run.id.toString());
        const hasOperations =
          opsCount.explainers > 0 || opsCount.predictions > 0;

        if (hasOperations) {
          // Show confirmation dialog
          setRunToRetrain(run);
          setOperationsCount(opsCount);
          setRetrainDialogOpen(true);
          return;
        }
      }

      // Proceed with training if no confirmation needed
      await executeTraining(run);
    } catch (error) {
      console.error("Error checking operations:", error);
      // If check fails, proceed with training anyway
      await executeTraining(run);
    }
  };

  const executeTraining = async (run) => {
    try {
      // Delete operations if they exist
      if (
        operationsCount &&
        (operationsCount.explainers > 0 || operationsCount.predictions > 0)
      ) {
        await deleteRunOperations(run.id.toString());
      }

      const updatedRun = await resetRunById(run.id.toString());

      const response = await enqueueRunnerJobRequest(run.id);

      if (!response || !response.id) {
        enqueueSnackbar(
          t("models:error.failedToStartRun", { runName: run.name }),
          {
            variant: "error",
          },
        );
        return;
      }

      enqueueSnackbar(t("models:message.runStarted", { runName: run.name }), {
        variant: "success",
      });

      setRuns((prevRuns) =>
        prevRuns.map((r) =>
          r.id === run.id ? { ...updatedRun, status: 1 } : r,
        ),
      );

      startJobPolling(
        response.id,
        async () => {
          const updated = await getRunById(run.id.toString());
          setRuns((prevRuns) =>
            prevRuns.map((r) => (r.id === run.id ? updated : r)),
          );
          enqueueSnackbar(
            t("models:message.runCompleted", { runName: run.name }),
            {
              variant: "success",
            },
          );
        },
        async (result) => {
          const updated = await getRunById(run.id.toString());
          setRuns((prevRuns) =>
            prevRuns.map((r) => (r.id === run.id ? updated : r)),
          );
          enqueueSnackbar(
            t("models:error.runFailed", {
              runName: run.name,
              error: result.error || t("common:unknownError"),
            }),
            { variant: "error" },
          );
        },
      );

      setRetrainDialogOpen(false);
      setRunToRetrain(null);
      setOperationsCount(null);
    } catch (error) {
      console.error("Error training run:", error);
      enqueueSnackbar(
        t("models:error.failedToStartRun", { runName: run.name }),
        {
          variant: "error",
        },
      );
    }
  };

  const handleConfirmRetrain = () => {
    if (runToRetrain) {
      executeTraining(runToRetrain);
    }
  };

  const handleCancelRetrain = () => {
    setRetrainDialogOpen(false);
    setRunToRetrain(null);
    setOperationsCount(null);
  };

  const handleEditRun = async (run) => {
    enqueueSnackbar("Edit functionality coming soon", { variant: "info" });
  };

  const handleDeleteRun = async (run) => {
    try {
      await deleteRun(run.id.toString());
      setRuns((prev) => prev.filter((r) => r.id !== run.id));
      enqueueSnackbar(t("models:message.runDeleted", { runName: run.name }), {
        variant: "success",
      });
    } catch (error) {
      console.error("Error deleting run:", error);
      enqueueSnackbar(
        t("models:error.failedToDeleteRun", { runName: run.name }),
        {
          variant: "error",
        },
      );
    }
  };

  const handleSessionEdit = async (sessionId, newName) => {
    try {
      const result = await updateExperiment({
        id: sessionId,
        formData: { name: newName },
      });
      setSessions((prev) =>
        prev.map((session) =>
          session.id === sessionId
            ? { ...session, name: result.name }
            : session,
        ),
      );
      enqueueSnackbar(t("models:message.sessionUpdated"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update session:", error);
      if (error.response?.status === 409) {
        enqueueSnackbar(t("models:error.sessionNameExists"), {
          variant: "error",
        });
      } else if (error.response?.status === 422) {
        enqueueSnackbar(t("models:error.sessionNameEmpty"), {
          variant: "error",
        });
      } else {
        enqueueSnackbar(t("models:error.failedToUpdateSession"), {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    setSelectedDatasetId(null);
    setSelectedTask(null);
    setStep(0);
  };

  const handleNewSessionFromDataset = () => {
    // Keep the selectedDatasetId but go to task selection
    setSelectedSessionId(null);
    setSelectedTask(null);
    setStep(0);
  };

  const handleBackToDataset = () => {
    // Go back to dataset visualization from task selection
    setSelectedTask(null);
    setStep(2);
  };

  const handleGoToDatasets = () => {
    navigate("/app/data");
  };

  const handleMouseMove = useCallback((e) => {
    if (isResizingLeft.current) {
      const container = document.querySelector('[data-container="models"]');
      const containerRect = container.getBoundingClientRect();
      const newWidth =
        ((e.clientX - containerRect.left) / containerRect.width) * 100;
      if (newWidth >= 15 && newWidth <= 40) {
        setLeftBarWidth(newWidth);
      }
    }

    if (isResizingRight.current) {
      const container = document.querySelector('[data-container="models"]');
      const containerRect = container.getBoundingClientRect();
      const newWidth =
        ((containerRect.right - e.clientX) / containerRect.width) * 100;
      if (newWidth >= 15 && newWidth <= 40) {
        setRightBarWidth(newWidth);
      }
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    isResizingLeft.current = false;
    isResizingRight.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, []);

  const handleToggleLeft = () => {
    setIsTogglingLeft(true);
    setLeftBarVisible(!leftBarVisible);
    setTimeout(() => setIsTogglingLeft(false), 300);
  };

  const handleToggleRight = () => {
    setIsTogglingRight(true);
    setRightBarVisible(!rightBarVisible);
    setTimeout(() => setIsTogglingRight(false), 300);
  };

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const centerWidth =
    leftBarVisible && rightBarVisible
      ? 100 - leftBarWidth - rightBarWidth
      : leftBarVisible
      ? 100 - leftBarWidth
      : rightBarVisible
      ? 100 - rightBarWidth
      : 100;

  return (
    <Box
      height="calc(100vh - 74px)"
      width="100%"
      display="flex"
      data-container="models"
    >
      {/* Left Panel */}
      <Box
        width={leftBarVisible ? `${leftBarWidth}%` : "0%"}
        position="relative"
        sx={{
          transition: isTogglingLeft
            ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease"
            : "none",
          opacity: leftBarVisible ? 1 : 0,
          overflow: "hidden",
        }}
      >
        {leftBarVisible && (
          <>
            <LeftBar
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              sessions={sessions}
              selectedSessionId={selectedSessionId}
              tasks={tasks}
              onDatasetClick={handleDatasetClick}
              onDatasetDelete={handleDatasetDelete}
              onDatasetEdit={handleDatasetEdit}
              onSessionClick={handleSessionClick}
              onSessionDelete={handleSessionDelete}
              onSessionEdit={handleSessionEdit}
              onToggle={handleToggleLeft}
              handleNewSessionButton={handleNewSessionButton}
            />
            <Box
              onMouseDown={() => {
                isResizingLeft.current = true;
                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
              }}
              sx={{
                position: "absolute",
                right: -2,
                top: 0,
                bottom: 0,
                width: "5px",
                cursor: "col-resize",
                bgcolor: "transparent",
                transition: "background-color 0.2s ease",
                "&:hover": {
                  bgcolor: "primary.main",
                },
                zIndex: 10,
              }}
            />
          </>
        )}
      </Box>

      {!leftBarVisible && (
        <IconButton
          onClick={handleToggleLeft}
          sx={{
            position: "absolute",
            left: 8,
            top: "50%",
            transform: "translateY(-50%)",
            bgcolor: "background.paper",
            zIndex: 10,
            transition: "all 0.2s ease",
            "&:hover": {
              bgcolor: "action.hover",
              transform: "translateY(-50%) scale(1.1)",
            },
          }}
        >
          <ChevronRight />
        </IconButton>
      )}

      {/* Center Panel */}
      <Box
        width={`${centerWidth}%`}
        sx={{
          transition:
            isTogglingLeft || isTogglingRight
              ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
              : "none",
        }}
      >
        <CenterBox>
          {selectedSessionId ? (
            <SessionVisualization
              session={selectedSession}
              runs={runs}
              onTrain={handleTrainRun}
              onEditRun={handleEditRun}
              onDeleteRun={handleDeleteRun}
            />
          ) : step === 1 && selectedTask ? (
            <CreateSessionSteps
              backHome={handleBackToTaskSelection}
              selectedTask={selectedTask}
              datasets={datasets}
              handleSessionCreated={handleSessionCreated}
              existingSessions={sessions}
              preselectedDatasetId={selectedDatasetId}
            />
          ) : step === 2 && selectedDatasetId ? (
            <DatasetVisualization
              dataset={datasets.find((d) => d.id === selectedDatasetId)}
              onItemCreated={handleSessionCreated}
              onNewItem={handleNewSessionFromDataset}
              existingItems={sessions}
              newItemButtonText="New Session"
            />
          ) : step === 0 ? (
            <SelectOptionMenu
              title={
                selectedDatasetId
                  ? t("models:label.selectTaskForSession")
                  : t("models:label.modelsModule")
              }
              subtitle={
                selectedDatasetId
                  ? t("models:label.chooseTaskForSessionWithDataset", {
                      datasetName: datasets.find(
                        (d) => d.id === selectedDatasetId,
                      )?.name,
                    })
                  : t("models:label.configureTasksTrainCompareModels")
              }
              options={tasks.map((task) => ({
                name: task.name,
                display_name:
                  task.metadata?.display_name ||
                  task.name
                    .replace("Task", "")
                    .replace(/([A-Z])/g, " $1")
                    .trim(),
                description:
                  task.description || task.metadata?.short_description || "",
                Icon: null,
              }))}
              searchBar={true}
              goToNextStep={handleTaskSelect}
              goToPrevStep={selectedDatasetId ? handleBackToDataset : null}
              showNoDatasetAlert={!selectedDatasetId && datasets.length === 0}
              onGoToDatasets={handleGoToDatasets}
            />
          ) : null}
        </CenterBox>
      </Box>

      {!rightBarVisible && (
        <IconButton
          onClick={handleToggleRight}
          sx={{
            position: "absolute",
            right: 8,
            top: "50%",
            transform: "translateY(-50%)",
            bgcolor: "background.paper",
            zIndex: 10,
            transition: "all 0.2s ease",
            "&:hover": {
              bgcolor: "action.hover",
              transform: "translateY(-50%) scale(1.1)",
            },
          }}
        >
          <ChevronLeft />
        </IconButton>
      )}

      {/* Right Panel */}
      <Box
        width={rightBarVisible ? `${rightBarWidth}%` : "0%"}
        position="relative"
        sx={{
          transition: isTogglingRight
            ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease"
            : "none",
          opacity: rightBarVisible ? 1 : 0,
          overflow: "hidden",
        }}
      >
        {rightBarVisible && (
          <>
            <Box
              onMouseDown={() => {
                isResizingRight.current = true;
                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
              }}
              sx={{
                position: "absolute",
                left: -2,
                top: 0,
                bottom: 0,
                width: "5px",
                cursor: "col-resize",
                bgcolor: "transparent",
                transition: "background-color 0.2s ease",
                "&:hover": {
                  bgcolor: "primary.main",
                },
                zIndex: 10,
              }}
            />
            <RightBar
              session={selectedSession}
              onToggle={handleToggleRight}
              onModelClick={handleModelClick}
            />
          </>
        )}
      </Box>

      {/* Add Model Dialog */}
      <AddModelDialog
        open={addModelDialogOpen}
        onClose={() => {
          setAddModelDialogOpen(false);
          setPreselectedModel(null);
        }}
        session={selectedSession}
        preselectedModel={preselectedModel}
        existingRuns={runs}
        onRunCreated={handleRunCreated}
      />

      {/* Retrain Confirmation Dialog */}
      <RetrainConfirmDialog
        open={retrainDialogOpen}
        onClose={handleCancelRetrain}
        onConfirm={handleConfirmRetrain}
        run={runToRetrain}
        operationsCount={operationsCount}
      />
    </Box>
  );
}
