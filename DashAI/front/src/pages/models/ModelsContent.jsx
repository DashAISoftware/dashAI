import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { TourProvider } from "../../components/tour/TourProvider";
import { TOUR_KEYS } from "../../constants/tours";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import ModelsLeftBar from "../../components/models/ModelsLeftBar";
import ModelsRightBar from "../../components/models/ModelsRightBar";
import SessionVisualization from "../../components/models/SessionVisualization";
import ModelsCenterContent from "../../components/models/ModelCenterContent";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useModels } from "../../components/models/ModelsContext";

export default function ModelsContent() {
  const location = useLocation();
  const threePanelLayout = useThreePanelLayout();
  const { t } = useTranslation(["models"]);

  const {
    sessions,
    step,
    setStep,
    selectedSessionId,
    setSelectedSessionId,
    setSelectedSession,
    setRuns,
    fetchRuns,
  } = useModels();

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

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <TourProvider
        tourKey={TOUR_KEYS.MODELS}
        disabled={step !== 0}
        disabledMessage={t("models:label.tourDisabledMessage")}
      >
        <ModuleContainer>
          {/* Left Panel */}
          <LeftPanel data-tour="models-left-panel">
            <ModelsLeftBar onToggle={threePanelLayout.handleToggleLeft} />
          </LeftPanel>
          {selectedSessionId ? (
            <TourProvider tourKey={TOUR_KEYS.MODELS_SESSION}>
              <CenterPanel data-tour="models-center-panel">
                <SessionVisualization />
              </CenterPanel>
              <RightPanel data-tour="models-right-panel" toggleButtonTop="50%">
                <ModelsRightBar onToggle={threePanelLayout.handleToggleRight} />
              </RightPanel>
            </TourProvider>
          ) : (
            <>
              <CenterPanel data-tour="models-center-panel">
                <ModelsCenterContent />
              </CenterPanel>

              {/* Right Panel */}
              <RightPanel data-tour="models-right-panel" toggleButtonTop="50%">
                <ModelsRightBar onToggle={threePanelLayout.handleToggleRight} />
              </RightPanel>
            </>
          )}
        </ModuleContainer>
      </TourProvider>
    </ThreePanelLayoutContext.Provider>
  );
}
