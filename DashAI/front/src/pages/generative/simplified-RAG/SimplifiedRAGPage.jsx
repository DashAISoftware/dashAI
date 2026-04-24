import { useState, useEffect, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Box } from "@mui/material";
import ModuleContainer from "../../../components/layout/ModuleContainer";
import LeftPanel from "../../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../../components/generative/SessionBar";
import DocumentsBar from "../../../components/generative/RAG/DocumentsBar";
import GenerativeChat from "../../../components/generative/GenerativeChat";
import RAGSessionSummary from "../../../components/generative/RAG/RAGSessionSummary";
import { removeSession } from "../../../api/session";
import { useGenerative } from "../../../components/generative/GenerativeContext";
import { useThreePanelLayout } from "../../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { FormSchemaProvider } from "../../../contexts/schema";
import DocumentSelectionPhase from "./DocumentSelectionPhase";
import SimplifiedSessionSetup from "./SimplifiedSessionSetup";

function SimplifiedRAGPage({ onSessionSelect, sessions, setSessions }) {
  const navigate = useNavigate();
  const location = useLocation();
  const threePanelLayout = useThreePanelLayout();
  const generative = useGenerative() ?? {};

  const {
    sessions: contextSessions,
    setSessions: setContextSessions,
    selectedSessionId: globalSelectedSessionId,
    setSelectedSessionId: setGlobalSelectedSessionId,
    selectedTaskName,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
  } = generative;

  const currentSessions = sessions || contextSessions || [];
  const currentSetSessions = setSessions || setContextSessions;

  // Phase management
  const [currentPhase, setCurrentPhase] = useState("document-selection"); // "document-selection" or "setup"
  const [sessionData, setSessionData] = useState(null);

  const sessionSelectionState =
    location.state?.selectedSessionId != null ? location.state : null;

  useEffect(() => {
    if (!sessionSelectionState?.selectedSessionId) return;

    const nextTaskName =
      sessionSelectionState.taskName ??
      sessionSelectionState.selectedTaskName ??
      selectedTaskName ??
      "RAGTask";
    const nextDisplayName =
      sessionSelectionState.taskDisplayName ??
      sessionSelectionState.selectedDisplayName ??
      null;

    setGlobalSelectedSessionId?.(sessionSelectionState.selectedSessionId);
    setSelectedTaskName?.(nextTaskName);
    setSelectedDisplayName?.(nextDisplayName);
    setStepIndex?.(0);

    navigate(location.pathname, { replace: true, state: null });
  }, [
    sessionSelectionState,
    selectedTaskName,
    setGlobalSelectedSessionId,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
    navigate,
    location.pathname,
  ]);

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    if (onSessionSelect) {
      onSessionSelect(sessionId, taskName, taskDisplayName);
      return;
    }

    setGlobalSelectedSessionId?.(sessionId);
    setSelectedTaskName?.(taskName);
    setSelectedDisplayName?.(taskDisplayName);
    setStepIndex?.(0);
  };

  const handleNewSessionButton = () => {
    setGlobalSelectedSessionId?.(null);
    setSelectedTaskName?.("");
    setSelectedDisplayName?.(null);
    setStepIndex?.(0);
    // Reset to document selection phase
    setCurrentPhase("document-selection");
    setSessionData(null);
  };

  const handleSessionDelete = async (id) => {
    currentSetSessions?.((prev) => prev.filter((s) => s.id !== id));
    if (id === globalSelectedSessionId) {
      setGlobalSelectedSessionId?.(null);
    }
    await removeSession(id);
  };

  const handleDocumentsSelected = (data) => {
    // data contains: name, description, documents
    setSessionData(data);
    setCurrentPhase("setup");
  };

  const handleBackFromSetup = () => {
    setCurrentPhase("document-selection");
    setSessionData(null);
  };

  const handleCloseSetup = () => {
    setCurrentPhase("document-selection");
    setSessionData(null);
  };

  const centerContent =
    currentPhase === "document-selection" ? (
      <DocumentSelectionPhase onNext={handleDocumentsSelected} />
    ) : (
      <SimplifiedSessionSetup
        initialData={sessionData}
        onBack={handleBackFromSetup}
        onClose={handleCloseSetup}
      />
    );

  return (
    <FormSchemaProvider>
      <ThreePanelLayoutContext.Provider value={threePanelLayout}>
        <ModuleContainer>
          <LeftPanel data-tour="sessions-left-panel">
            <SessionBar
              sessions={currentSessions}
              selectedSessionId={globalSelectedSessionId}
              handleSessionClick={handleSessionClick}
              handleNewSessionButton={handleNewSessionButton}
              handleSessionDelete={handleSessionDelete}
              stepIndex={0}
              onToggle={threePanelLayout.handleToggleLeft}
            />
          </LeftPanel>

          <CenterPanel data-tour="task-gallery">
            {centerContent}
          </CenterPanel>

          <RightPanel toggleButtonTop="50%" data-tour="parameters-right-panel">
            <Box
              width="100%"
              height="100%"
              sx={{
                backgroundColor: "background.box",
                borderRadius: 2,
                minWidth: 0,
                maxWidth: "100%",
                overflow: "hidden",
              }}
            >
              <DocumentsBar
                selectedSessionId={null}
                taskName="RAGTask"
              />
            </Box>
          </RightPanel>
        </ModuleContainer>
      </ThreePanelLayoutContext.Provider>
    </FormSchemaProvider>
  );
}

export default SimplifiedRAGPage;
