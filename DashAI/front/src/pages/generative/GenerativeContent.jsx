import { useEffect } from "react";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../components/generative/SessionBar";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import RAGDocumentsPanel from "../../components/generative/RAG/RAGDocumentsPanel";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useTourContext } from "../../components/tour/TourProvider";
import { useGenerative } from "../../components/generative/GenerativeContext";
import { useTranslation } from "react-i18next";
import { useNavigate, useLocation } from "react-router-dom";
import RAGHomePage from "./RAG/RAGHomePage";

export default function GenerativeContent() {
  const threePanelLayout = useThreePanelLayout({ storageKey: "generative" });
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
  const { setDisabled } = useTourContext() ?? {};
  const { t } = useTranslation(["generative"]);
  const navigate = useNavigate();
  const location = useLocation();

  const isRagRoute = location.pathname.toLowerCase().startsWith("/app/generative/rag");

  // Acepta state de selección aunque no venga con fromSessionSelection
  const sessionSelectionState =
    location.state?.selectedSessionId != null ? location.state : null;

  useEffect(() => {
    if (!sessionSelectionState?.selectedSessionId) return;

    const nextTaskName =
      sessionSelectionState.taskName ??
      sessionSelectionState.selectedTaskName ??
      selectedTaskName ??
      null;
    const nextDisplayName =
      sessionSelectionState.taskDisplayName ??
      sessionSelectionState.selectedDisplayName ??
      selectedDisplayName ??
      null;

    setSelectedSessionId?.(sessionSelectionState.selectedSessionId);
    setSelectedTaskName?.(nextTaskName);
    setSelectedDisplayName?.(nextDisplayName);
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

    if (!isRagRoute && selectedTaskName === "RAGTask") {
      navigate("/app/generative/rag", {
        replace: true,
        state: selectedSessionId
          ? {
              selectedSessionId,
              taskName: selectedTaskName,
              taskDisplayName: selectedDisplayName ?? null,
            }
          : null,
      });
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

  useEffect(() => {
    setDisabled?.(
      stepIndex !== 0 || !!selectedSessionId,
      t("generative:label.tourDisabledMessage"),
    );
  }, [stepIndex, selectedSessionId, setDisabled, t]);

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
          {selectedSessionId && selectedTaskName === "RAGTask" ? (
            <RAGDocumentsPanel
              selectedSessionId={selectedSessionId}
              isRagChatActive={true}
            />
          ) : (
            <ParamsBar onToggle={threePanelLayout.handleToggleRight} />
          )}
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
