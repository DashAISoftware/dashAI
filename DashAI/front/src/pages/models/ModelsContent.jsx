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
import RetrainConfirmDialog from "../../components/models/RetrainConfirmDialog";
import { updateModelSession, deleteModelSession } from "../../api/modelSession";
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
import { useTranslation } from "react-i18next";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useModels } from "../../components/models/ModelsContext";

export default function ModelsContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [runs, setRuns] = useState([]);
  const [retrainDialogOpen, setRetrainDialogOpen] = useState(false);
  const [runToRetrain, setRunToRetrain] = useState(null);
  const [operationsCount, setOperationsCount] = useState(null);

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "datasets", "common"]);
  const tourContext = useTourContext(); // This is for MODELS tour

  const threePanelLayout = useThreePanelLayout();

  const {
    datasets,
    replaceDatasets,
    selectedDatasetId,
    selectDataset,
    fetchDatasets,
    editDataset,
    deleteDataset,
    sessions,
    setSessions,
    tasks,
    fetchSessions,
    fetchTasks,
    editSession,
    step,
    setStep,
  } = useModels();

  useEffect(() => {
    fetchDatasets();
    fetchSessions();
    fetchTasks();
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
    selectDataset(datasetId);
    setSelectedSessionId(null);
    setSelectedTask(null);
    setStep(2); // Use a different step to show DatasetVisualization
  };

  const handleDatasetDelete = (id) => {
    if (id === selectedDatasetId) {
      selectDataset(null);
      setStep(0);
      setSelectedTask(null);
    }

    replaceDatasets((prevDatasets) =>
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

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    selectDataset(null);
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
            onDatasetEdit={editDataset}
            onSessionClick={handleSessionClick}
            onSessionEdit={editSession}
            onToggle={threePanelLayout.handleToggleLeft}
            handleNewSessionButton={handleNewSessionButton}
          />
        </LeftPanel>
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
                  goToPrevStep={selectedDatasetId ? handleBackToDataset : null}
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
