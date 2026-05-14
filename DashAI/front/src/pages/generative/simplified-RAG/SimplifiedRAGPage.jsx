import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Box } from "@mui/material";
import ModuleContainer from "../../../components/layout/ModuleContainer";
import LeftPanel from "../../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../../components/generative/SessionBar";
import GenerativeChat from "../../../components/generative/GenerativeChat";
import RAGSessionSummary from "../../../components/generative/RAG/RAGSessionSummary";
import { removeSession } from "../../../api/session";
import { useGenerative } from "../../../components/generative/GenerativeContext";
import { useThreePanelLayout } from "../../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { FormSchemaProvider } from "../../../contexts/schema";
import SimplifiedSessionSetup from "./SimplifiedSessionSetup";
import RAGDocumentsPanel from "../../../components/generative/RAG/RAGDocumentsPanel";
import SimplifiedRAGInfoBar from "../../../components/generative/RAG/SimplifiedRAGInfoBar";
import RAGParamsPanel from "../../../components/generative/RAG/RAGParamsPanel";

function SimplifiedRAGPage({ onSessionSelect, sessions, setSessions }) {
  const navigate = useNavigate();
  const location = useLocation();
  const threePanelLayout = useThreePanelLayout();
  const generative = useGenerative() ?? {};

  const [showRagChat, setShowRagChat] = useState(false);
  const [activeRagChatSessionId, setActiveRagChatSessionId] = useState(null);

  const {
    sessions: contextSessions,
    setSessions: setContextSessions,
    selectedSessionId: globalSelectedSessionId,
    setSelectedSessionId: setGlobalSelectedSessionId,
    selectedTaskName,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
    fetchSessions,
  } = generative;

  const currentSessions = sessions || contextSessions || [];
  const currentSetSessions = setSessions || setContextSessions;

  useEffect(() => {
    if (currentSessions.length === 0 && fetchSessions) {
      fetchSessions();
    }
  }, []);

  const isRagSessionSelected =
    selectedTaskName === "RAGTask" && Boolean(globalSelectedSessionId);
  const isRagChatActive = showRagChat && activeRagChatSessionId === globalSelectedSessionId;

  const [setupKey, setSetupKey] = useState(0);

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
    setShowRagChat(false);
    setActiveRagChatSessionId(null);

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

  useEffect(() => {
    if (!isRagSessionSelected) {
      setShowRagChat(false);
      setActiveRagChatSessionId(null);
    }
  }, [isRagSessionSelected, globalSelectedSessionId]);

  useEffect(() => {
    setShowRagChat(false);
    setActiveRagChatSessionId(null);
  }, [globalSelectedSessionId]);

  const handleStartRagChat = () => {
    setShowRagChat(true);
    setActiveRagChatSessionId(globalSelectedSessionId);
  };

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    if (onSessionSelect) {
      onSessionSelect(sessionId, taskName, taskDisplayName);
      return;
    }

    setGlobalSelectedSessionId?.(sessionId);
    setSelectedTaskName?.(taskName);
    setSelectedDisplayName?.(taskDisplayName);
    setStepIndex?.(0);
    setShowRagChat(false);
    setActiveRagChatSessionId(null);

    if (taskName === "RAGTask") {
      navigate("/app/generative/rag", {
        replace: true,
        state: {
          selectedSessionId: sessionId,
          taskName,
          taskDisplayName,
          fromSessionSelection: true,
        },
      });
      return;
    }

    if (taskName !== "RAGTask") {
      navigate("/app/generative", {
        replace: true,
        state: {
          selectedSessionId: sessionId,
          taskName,
          taskDisplayName,
          fromSessionSelection: true,
        },
      });
    }
  };

  const handleNewSessionButton = async () => {
    setGlobalSelectedSessionId?.(null);
    setSelectedTaskName?.("");
    setSelectedDisplayName?.(null);
    setStepIndex?.(0);
    setShowRagChat(false);
    setActiveRagChatSessionId(null);
    if (fetchSessions) await fetchSessions();
    setSetupKey((prev) => prev + 1);
  };

  const handleSessionDelete = async (id) => {
    currentSetSessions?.((prev) => prev.filter((s) => s.id !== id));
    if (id === globalSelectedSessionId) {
      setGlobalSelectedSessionId?.(null);
    }
    await removeSession(id);
  };

  const handleCloseSetup = () => {
    setSetupKey((prev) => prev + 1);
  };

  const handleSessionCreated = (createdSession) => {
    if (!createdSession?.id) return;

    currentSetSessions?.((prev) => {
      const nextSessions = Array.isArray(prev) ? prev.slice() : [];
      const exists = nextSessions.some((session) => session.id === createdSession.id);
      if (!exists) {
        nextSessions.unshift(createdSession);
      }
      return nextSessions;
    });

    navigate("/app/generative/rag", {
      replace: true,
      state: {
        selectedSessionId: createdSession.id,
        taskName: "RAGTask",
        taskDisplayName: "RAG",
        fromSessionSelection: true,
      },
    });
  };

  const centerContent = isRagSessionSelected ? (
    isRagChatActive ? (
      <GenerativeChat />
    ) : (
      <RAGSessionSummary
        sessionId={globalSelectedSessionId}
        onStartChat={handleStartRagChat}
      />
    )
  ) : (
    <SimplifiedSessionSetup
      key={setupKey}
      onClose={handleCloseSetup}
      onSessionCreated={handleSessionCreated}
      existingSessions={currentSessions}
    />
  );

  return (
    <FormSchemaProvider>
      <ThreePanelLayoutContext.Provider value={threePanelLayout}>
        <ModuleContainer>
          <LeftPanel data-tour="sessions-left-panel">
            {isRagSessionSelected ? (
              <Box sx={{ display: "flex", flexDirection: "column", height: "100%", gap: 1 }}>
                <Box sx={{ flex: "0 0 60%", minHeight: 0 }}>
                  <RAGDocumentsPanel
                    selectedSessionId={globalSelectedSessionId}
                    isRagChatActive={isRagChatActive}
                  />
                </Box>

                <Box sx={{ flex: "0 0 40%", overflow: "auto", minHeight: 0 }}>
                  <SessionBar
                    sessions={currentSessions}
                    selectedSessionId={globalSelectedSessionId}
                    handleSessionClick={handleSessionClick}
                    handleNewSessionButton={handleNewSessionButton}
                    handleSessionDelete={handleSessionDelete}
                    stepIndex={0}
                    onToggle={threePanelLayout.handleToggleLeft}
                    showSearch={false}
                  />
                </Box>
              </Box>
            ) : (
              <SessionBar
                sessions={currentSessions}
                selectedSessionId={globalSelectedSessionId}
                handleSessionClick={handleSessionClick}
                handleNewSessionButton={handleNewSessionButton}
                handleSessionDelete={handleSessionDelete}
                stepIndex={0}
                onToggle={threePanelLayout.handleToggleLeft}
                showSearch={false}
              />
            )}
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
                overflow: "auto",
                p: 2,
              }}
            >
              {isRagSessionSelected ? (
                <RAGParamsPanel selectedSessionId={globalSelectedSessionId} />
              ) : (
                <SimplifiedRAGInfoBar />
              )}
            </Box>
          </RightPanel>
        </ModuleContainer>
      </ThreePanelLayoutContext.Provider>
    </FormSchemaProvider>
  );
}

export default SimplifiedRAGPage;
