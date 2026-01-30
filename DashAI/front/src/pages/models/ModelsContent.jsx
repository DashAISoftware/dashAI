import { useState, useEffect, useRef, useCallback } from "react";
import { useSnackbar } from "notistack";
import { useLocation, useNavigate } from "react-router-dom";
import { useTourContext } from "../../components/tour/TourProvider";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import LeftBar from "../../components/models/LeftBar";
import RightBar from "../../components/models/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import CreateSessionSteps from "../../components/models/CreateSessionSteps";
import SessionVisualization from "../../components/models/SessionVisualization";
import DatasetVisualization from "../../components/DatasetVisualization";
import AddModelDialog from "../../components/models/AddModelDialog";
import {
  ModelProvider,
  useModelContext,
} from "../../components/models/ModelProvider";
import RetrainConfirmDialog from "../../components/models/RetrainConfirmDialog";
import { getComponents } from "../../api/component";
import {
  getDatasets,
  getDatasetInfo,
  updateDataset,
  deleteDataset,
} from "../../api/datasets";
import {
  getModelSessions,
  updateModelSession,
  deleteModelSession,
} from "../../api/modelSession";
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
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";

export default function ModelsContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [runs, setRuns] = useState([]);
  // Eliminados: addModelDialogOpen, setAddModelDialogOpen, preselectedModel, setPreselectedModel

  const [retrainDialogOpen, setRetrainDialogOpen] = useState(false);
  const [runToRetrain, setRunToRetrain] = useState(null);
  const [operationsCount, setOperationsCount] = useState(null);

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "datasets", "common"]);
  const tourContext = useTourContext(); // This is for MODELS tour

  const threePanelLayout = useThreePanelLayout();
  const sessionTourContext = useTourContext();

  // Component to handle session tour context
  const SessionTourHandler = () => {
    const sessionTourContext = useTourContext(); // This is for MODELS_SESSION tour

    // Check if tour should start from previous tutorial
    useEffect(() => {
      const shouldStartTour = sessionStorage.getItem("startModelsSessionTour");
      if (shouldStartTour === "true" && sessionTourContext) {
        sessionStorage.removeItem("startModelsSessionTour");
        setTimeout(() => {
          sessionTourContext.startTour();
        }, 1000);
      }
    }, [sessionTourContext]);

    // Listen for clicks on the Graphs button
    useEffect(() => {
      const handleGraphsButtonClick = (e) => {
        const graphsButton = e.target.closest('[data-tour="graphs-button"]');
        if (graphsButton && sessionTourContext?.stepIndex === 7) {
          setTimeout(() => {
            sessionTourContext.nextStep();
          }, 500);
        }
      };

      document.addEventListener("click", handleGraphsButtonClick, true);
      return () => {
        document.removeEventListener("click", handleGraphsButtonClick, true);
      };
    }, [sessionTourContext]);

    const handleRunCreatedWithTour = (newRun) => {
      handleRunCreated(newRun);

      // Advance tour after creating run (step 3 -> 4)
      if (sessionTourContext?.run && sessionTourContext?.stepIndex === 3) {
        setTimeout(() => {
          // Scroll to the newly created run card
          const runCard = document.querySelector(
            '[data-tour="first-run-card"]',
          );
          if (runCard) {
            runCard.scrollIntoView({
              behavior: "smooth",
              block: "center",
              inline: "nearest",
            });
          }

          // Advance to next step after scroll completes
          setTimeout(() => {
            sessionTourContext.nextStep();
          }, 300);
        }, 500);
      }
    };

    const handleTrainRunWithTour = (run) => {
      handleTrainRun(run);

      // Advance tour after clicking train (step 5 -> end)
      if (sessionTourContext?.run && sessionTourContext?.stepIndex === 5) {
        setTimeout(() => {
          sessionTourContext.nextStep();
        }, 500);
      }
    };

    return (
      <>
        {/* Center Panel - Session */}

        <CenterPanel data-tour="models-center-panel">
          <SessionVisualization
            session={selectedSession}
            runs={runs}
            onTrain={handleTrainRunWithTour}
            onEditRun={handleEditRun}
            onDeleteRun={handleDeleteRun}
          />
        </CenterPanel>

        <RightPanel data-tour="models-right-panel" toggleButtonTop="50%">
          <RightBar
            session={selectedSession}
            onToggle={threePanelLayout.handleToggleRight}
          />
        </RightPanel>

        <TourButton tourKey={TOUR_KEYS.MODELS_SESSION} />

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
          onRunCreated={handleRunCreatedWithTour}
        />
      </>
    );
  };

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
  }, [enqueueSnackbar, t]);

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
        const data = await getModelSessions();
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

      setRuns(data);
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

    if (tourContext?.run && tourContext?.stepIndex === 4) {
      const waitForElement = () => {
        const element = document.querySelector(
          '[data-tour="models-dataset-selection"]',
        );
        if (element) {
          tourContext.nextStep();
        } else {
          setTimeout(waitForElement, 100);
        }
      };
      setTimeout(waitForElement, 100);
    }
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
      await deleteModelSession(sessionId.toString());
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

  const handleRunCreated = (newRun) => {
    setRuns((prev) => [...prev, newRun]);
    enqueueSnackbar(t("models:message.runAdded", { runName: newRun.name }), {
      variant: "success",
    });

    // Advance tour after creating run (step 3 -> 4)
    if (sessionTourContext?.run && sessionTourContext?.stepIndex === 3) {
      setTimeout(() => {
        // Scroll to the newly created run card
        const runCard = document.querySelector('[data-tour="first-run-card"]');
        if (runCard) {
          runCard.scrollIntoView({
            behavior: "smooth",
            block: "center",
            inline: "nearest",
          });
        }

        // Advance to next step after scroll completes
        setTimeout(() => {
          sessionTourContext.nextStep();
        }, 300);
      }, 500);
    }
  };

  const handleTrainRun = async (run) => {
    try {
      // Check if run has been trained before (has metrics)
      const hasBeenTrained =
        run.test_metrics ||
        run.train_metrics ||
        run.validation_metrics ||
        run.status === 3; // Finished

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
      const result = await updateModelSession({
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

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        {/* Left Panel */}
        <LeftPanel data-tour="models-left-panel">
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
            onToggle={threePanelLayout.handleToggleLeft}
            handleNewSessionButton={handleNewSessionButton}
          />
        </LeftPanel>
        <ModelProvider>
          {selectedSessionId ? (
            <TourProvider tourKey={TOUR_KEYS.MODELS_SESSION}>
              <CenterPanel data-tour="models-center-panel">
                <SessionVisualization
                  session={selectedSession}
                  runs={runs}
                  onTrain={handleTrainRun}
                  onEditRun={handleEditRun}
                  onDeleteRun={handleDeleteRun}
                />
              </CenterPanel>
              <RightPanel data-tour="models-right-panel" toggleButtonTop="50%">
                <RightBar
                  session={selectedSession}
                  existingRuns={runs}
                  onRunCreated={handleRunCreated}
                  onToggle={threePanelLayout.handleToggleRight}
                />
              </RightPanel>
              <TourButton tourKey={TOUR_KEYS.MODELS_SESSION} />
            </TourProvider>
          ) : (
            <>
              <CenterPanel data-tour="models-center-panel">
                {step === 1 && selectedTask ? (
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
                    newItemButtonText={t("models:button.createSession")}
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
                        task.display_name ||
                        task.name
                          .replace("Task", "")
                          .replace(/([A-Z])/g, " $1")
                          .trim(),
                      description:
                        task.description ||
                        task.metadata?.short_description ||
                        "",
                      Icon: null,
                    }))}
                    searchBar={true}
                    goToNextStep={handleTaskSelect}
                    goToPrevStep={
                      selectedDatasetId ? handleBackToDataset : null
                    }
                    showNoDatasetAlert={
                      !selectedDatasetId && datasets.length === 0
                    }
                    onGoToDatasets={handleGoToDatasets}
                  />
                ) : null}
              </CenterPanel>

              {/* Right Panel */}
              <RightPanel data-tour="models-right-panel" toggleButtonTop="50%">
                <RightBar
                  session={selectedSession}
                  onToggle={threePanelLayout.handleToggleRight}
                />
              </RightPanel>
            </>
          )}

          {/* Retrain Confirmation Dialog */}
          <RetrainConfirmDialog
            open={retrainDialogOpen}
            onClose={handleCancelRetrain}
            onConfirm={handleConfirmRetrain}
            run={runToRetrain}
            operationsCount={operationsCount}
          />
        </ModelProvider>
      </ModuleContainer>
      {!selectedSessionId && (
        <TourButton
          tourKey={TOUR_KEYS.MODELS}
          disabled={step !== 0}
          disabledMessage="Return to home to start the tour"
        />
      )}
    </ThreePanelLayoutContext.Provider>
  );
}
