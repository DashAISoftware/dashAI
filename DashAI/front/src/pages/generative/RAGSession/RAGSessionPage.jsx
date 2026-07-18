import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Box } from "@mui/material";
import ModuleContainer from "../../../components/layout/ModuleContainer";
import LeftPanel from "../../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../../components/generative/SessionBar";
import GenerativeChat from "../../../components/generative/GenerativeChat";
import RAGSessionSummary from "../../../components/generative/RAG/RAGSessionSummary";
import { removeSession } from "../../../api/session";
import { getGenerativeSession } from "../../../api/generativeTask";
import { useGenerative } from "../../../components/generative/GenerativeContext";
import { useThreePanelLayout } from "../../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { FormSchemaProvider } from "../../../contexts/schema";
import RAGSessionSetup from "./RAGSessionSetup";
import RAGDocumentsPanel from "../../../components/generative/RAG/RAGDocumentsPanel";
import RAGInfoBar from "../../../components/generative/RAG/RAGInfoBar";
import RAGParamsPanel from "../../../components/generative/RAG/RAGParamsPanel";

/**
 * Top-level RAG session page with three-panel layout.
 * Manages session selection, chat activation, session creation, and deletion.
 *
 * @param {object}   props
 * @param {Function} [props.onSessionSelect]  - Override session selection behaviour.
 * @param {Array}    [props.sessions]         - Optional sessions list override.
 * @param {Function} [props.setSessions]      - Optional setter override.
 * @returns {JSX.Element} Three-panel RAG page.
 */
function RAGSessionPage({ onSessionSelect, sessions, setSessions }) {
  const navigate = useNavigate();
  const { id: urlSessionId } = useParams();
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

  /**
   * Parse and validate a raw session id from the URL.
   * @param {string|number} rawId - Raw id value.
   * @returns {number|null} Positive integer or null.
   */
  const resolveSessionId = useCallback(
    (rawId) => {
      const num = Number(rawId);
      return Number.isFinite(num) && num > 0 ? num : null;
    },
    [],
  );

  useEffect(() => {
    const sid = resolveSessionId(urlSessionId);
    if (!sid) return;
    if (sid === globalSelectedSessionId) return;

    const load = async () => {
      try {
        const session = await getGenerativeSession(sid);
        if (!session) return;
        setGlobalSelectedSessionId?.(sid);
        setSelectedTaskName?.(session.task_name);
        setStepIndex?.(0);
        setShowRagChat(false);
        setActiveRagChatSessionId(null);
      } catch {
        // session not found or error — ignore
      }
    };
    load();
  }, [urlSessionId, globalSelectedSessionId, resolveSessionId]);

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

  /**
   * Activate the RAG chat view for the currently selected session.
   */
  const handleStartRagChat = () => {
    setShowRagChat(true);
    setActiveRagChatSessionId(globalSelectedSessionId);
  };

  /**
   * Handle session selection from the SessionBar.
   * Updates context and navigates to the session URL.
   * @param {number} sessionId
   * @param {string} taskName
   * @param {string} taskDisplayName
   */
  const handleSessionClick = useCallback((sessionId, taskName, taskDisplayName) => {
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

    navigate(`/app/generative/sessions/${sessionId}`, { replace: true });
  }, [onSessionSelect, navigate, setGlobalSelectedSessionId, setSelectedTaskName, setSelectedDisplayName, setStepIndex]);

  /**
   * Reset state to show the RAG session setup form.
   */
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

  /**
   * Remove a session optimistically from local state and persist the deletion.
   * @param {number} id - Session id to delete.
   */
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

  /**
   * After a session is created, add it to the session list and navigate to it.
   * @param {object} createdSession - The newly created session object.
   */
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

    navigate(`/app/generative/sessions/${createdSession.id}`, { replace: true });
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
    <RAGSessionSetup
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
                <RAGInfoBar />
              )}
            </Box>
          </RightPanel>
        </ModuleContainer>
      </ThreePanelLayoutContext.Provider>
    </FormSchemaProvider>
  );
}

export default RAGSessionPage;
