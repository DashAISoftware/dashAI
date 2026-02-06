import { useState, useEffect, useCallback } from "react";
import { useSnackbar } from "notistack";
import { useLocation } from "react-router-dom";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import ModelsLeftBar from "../../components/models/ModelsLeftBar";
import RightBar from "../../components/models/RightBar";
import SessionVisualization from "../../components/models/SessionVisualization";
import RetrainConfirmDialog from "../../components/models/RetrainConfirmDialog";
import ModelsCenterContent from "../../components/models/ModelCenterContent";
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
  const [runs, setRuns] = useState([]);
  const [retrainDialogOpen, setRetrainDialogOpen] = useState(false);
  const [runToRetrain, setRunToRetrain] = useState(null);
  const [operationsCount, setOperationsCount] = useState(null);

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["models", "datasets", "common"]);

  const threePanelLayout = useThreePanelLayout();

  const {
    fetchDatasets,
    sessions,
    fetchSessions,
    fetchTasks,
    step,
    setStep,
    selectedSessionId,
    setSelectedSessionId,
    selectedSession,
    setSelectedSession,
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

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        {/* Left Panel */}
        <LeftPanel data-tour="models-left-panel">
          <ModelsLeftBar onToggle={threePanelLayout.handleToggleLeft} />
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
              <ModelsCenterContent />
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
