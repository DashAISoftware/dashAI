import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../components/generative/SessionBar";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import { useGenerative } from "../../components/generative/GenerativeContext";
import { useTranslation } from "react-i18next";
import { useNavigate, useLocation } from "react-router-dom";
import { useEffect } from "react";
import RAGHomePage from "./RAG/RAGHomePage";

export default function GenerativeContent() {
  const threePanelLayout = useThreePanelLayout();
  const {
    stepIndex,
    selectedSessionId,
    selectedTaskName,
    selectedDisplayName,
    setSelectedSessionId,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
  } = useGenerative();
  const { t } = useTranslation(["generative"]);
  const navigate = useNavigate();
  const location = useLocation();

  const isRagRoute = location.pathname.toLowerCase().startsWith("/app/generative/rag");

  // Acepta state de selección aunque no venga con fromSessionSelection
  const sessionSelectionState =
    location.state?.selectedSessionId != null ? location.state : null;

  useEffect(() => {
    if (!sessionSelectionState?.selectedSessionId) return;

    setSelectedSessionId?.(sessionSelectionState.selectedSessionId);
    setSelectedTaskName?.(sessionSelectionState.taskName ?? selectedTaskName ?? null);
    setSelectedDisplayName?.(sessionSelectionState.taskDisplayName ?? selectedDisplayName ?? null);
    setStepIndex?.(0);

    navigate(location.pathname, { replace: true, state: null });
  }, [
    sessionSelectionState,
    setSelectedSessionId,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
    navigate,
    location.pathname,
    selectedTaskName,
    selectedDisplayName,
  ]);

  useEffect(() => {
    if (sessionSelectionState) return;

    if (
      isRagRoute &&
      selectedSessionId &&
      selectedTaskName &&
      selectedTaskName !== "RAGTask"
    ) {
      navigate("/app/generative", {
        replace: true,
        state: {
          selectedSessionId,
          taskName: selectedTaskName,
          taskDisplayName: selectedDisplayName ?? null,
        },
      });
      return;
    }

    if (
      !isRagRoute &&
      selectedTaskName === "RAGTask" &&
      !selectedSessionId &&
      stepIndex > 0
    ) {
      navigate("/app/generative/RAG", { replace: true });
    }
  }, [
    sessionSelectionState,
    isRagRoute,
    navigate,
    selectedSessionId,
    selectedTaskName,
    selectedDisplayName,
    stepIndex,
  ]);

  if (isRagRoute) {
    return <RAGHomePage />;
  }

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel data-tour="sessions-left-panel">
          <SessionBar onToggle={threePanelLayout.handleToggleLeft} />
        </LeftPanel>

        <CenterPanel data-tour="task-gallery">
          {selectedSessionId ? (
            <GenerativeChat />
          ) : stepIndex === 0 ? (
            <SelectTaskMenu />
          ) : (
            <SelectModelMenu />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%" data-tour="parameters-right-panel">
          <ParamsBar onToggle={threePanelLayout.handleToggleRight} />
          <TourButton
            tourKey={TOUR_KEYS.GENERATIVE}
            disabled={stepIndex !== 0 || selectedSessionId}
            disabledMessage={t("generative:label.tourDisabledMessage")}
          />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
