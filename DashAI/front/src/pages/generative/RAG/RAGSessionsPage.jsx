import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Box, CircularProgress, Typography } from "@mui/material";
import SessionBar from "../../../components/generative/SessionBar";
import MainGenerativeBox from "../../../components/generative/MainGenerativeBox";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import DocumentsBar from "../../../components/generative/RAG/DocumentsBar";
import NewSessionModal from "./NewSessionModal/NewSessionModal";
import RAGSessionsTable from "./RAGSessionsTable";
import { FormSchemaProvider } from "../../../contexts/schema";
import {
  getRAGSessions,
  createRAGSession,
} from "../../../api/rag";
import { getSessions, removeSession } from "../../../api/session";
import CenterBox from "../../../components/threeSectionLayout/panelContainers/CenterBox";

function RAGSessionsPage() {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editingSession, setEditingSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [documentRefreshTrigger, setDocumentRefreshTrigger] = useState(0);
  const ragSessions = sessions.filter((s) => s.task_name === "RAGTask");

  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      const allSessions = await getSessions();
      setSessions(allSessions);
    } catch (error) {
      console.error("RAGSessionsPage: Error loading sessions:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleOpenNewSessionModal = (session = null) => {
    setEditingSession(session);
    setShowModal(true);
  };

  const handleCreateOrUpdateSession = async (sessionData) => {
    try {
      const savedSession = await createRAGSession(sessionData);
      await loadSessions();
      setShowModal(false);
      return savedSession;
    } catch (error) {
      console.error("RAGSessionsPage: Error saving session:", error);
      throw error;
    }
  };

  const handleRemoveSession = useCallback(
    async (id) => {
      const numericId = typeof id === "string" ? parseInt(id, 10) : id;
      setSessions((prev) => prev.filter((s) => s.id !== numericId));
      await removeSession(id);
    },
    [],
  );

  const handleSessionSelect = (sessionId) => {
    // Navigate back to generative page with selected session
    navigate("/app/generative", { state: { selectedSessionId: sessionId } });
  };

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    // Instead of setting local state, navigate directly to generative with session
    navigate("/app/generative", { 
      state: { 
        selectedSessionId: sessionId,
        selectedTaskName: taskName,
        selectedDisplayName: taskDisplayName
      } 
    });
  };

  const handleNewSessionButton = () => {
    // The new session modal is handled locally, so just open it
    setShowModal(true);
  };

  const handleSessionDelete = (id) => {
    handleRemoveSession(id);
  };

  const handleDocumentChange = () => {
    setDocumentRefreshTrigger((prev) => prev + 1);
  };

  return (
    <FormSchemaProvider>
      <Box height="calc(100vh - 74px)" width="100%" display="flex">
        <Box width="20%">
          <SessionBar
            sessions={sessions}
            handleSessionClick={handleSessionClick}
            handleNewSessionButton={handleNewSessionButton}
            handleSessionDelete={handleSessionDelete}
            stepIndex={0}
          />
        </Box>

        <Box width="60%">
          <CenterBox>
              <RAGBreadcrumbs />
              <Typography variant="h5" component="h1">
                RAG Sessions
              </Typography>
              <Typography variant="subtitle1" component="p" sx={{ mb: 2 }}>
                Manage your RAG sessions: view existing sessions and create new ones for enhanced AI conversations.
              </Typography>

              <NewSessionModal
                open={showModal}
                onClose={() => {
                  setShowModal(false);
                  setEditingSession(null);
                }}
                onSessionSaved={handleCreateOrUpdateSession}
                onSessionSelect={handleSessionSelect}
                session={editingSession}
                existingSessions={ragSessions}
              />

              {loading ? (
                <Box display="flex" justifyContent="center" mt={4}>
                  <CircularProgress />
                </Box>
              ) : (
                <RAGSessionsTable
                  sessions={ragSessions.map((s) => ({ ...s, id: String(s.id) }))}
                  onEdit={(session) => handleOpenNewSessionModal(session)}
                  onSelect={handleSessionSelect}
                  onRefreshSessions={loadSessions}
                  onOpenNewSessionModal={() => handleOpenNewSessionModal()}
                  onRemove={handleRemoveSession}
                  showTableTitle={false}
                />
              )}
          </CenterBox>
        </Box>

        <Box width="20%" sx={{ flexShrink: 0, flexGrow: 0 }}>
          <Box
            width="100%"
            height="100%"
            sx={{ 
              backgroundColor: "background.box", 
              borderRadius: 2,
              minWidth: 0,
              maxWidth: "100%",
              overflow: "hidden"
            }}
          >
            <DocumentsBar
              selectedSessionId={null}
              taskName="RAGTask"
              onDocumentChange={handleDocumentChange}
              key={`documents-sessions-${documentRefreshTrigger}`}
            />
          </Box>
        </Box>
      </Box>
    </FormSchemaProvider>
  );
}

export default RAGSessionsPage;