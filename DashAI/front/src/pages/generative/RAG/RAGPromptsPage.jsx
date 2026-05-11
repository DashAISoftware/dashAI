import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Typography } from "@mui/material";
import SessionBar from "../../../components/generative/SessionBar";
import MainGenerativeBox from "../../../components/generative/MainGenerativeBox";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import RAGDocumentsPanel from "../../../components/generative/RAG/RAGDocumentsPanel";
import PromptSelectionTable from "../../../components/generative/RAG/PromptSelectionTable";
import { getSessions, removeSession } from "../../../api/session";
import CenterBox from "../../../components/threeSectionLayout/panelContainers/CenterBox";


function RAGPromptsPage() {
  const navigate = useNavigate();
  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [documentRefreshTrigger, setDocumentRefreshTrigger] = useState(0);

  const loadSessions = useCallback(async () => {
    try {
      const allSessions = await getSessions();
      setSessions(allSessions);
    } catch (error) {
      console.error("RAGPromptsPage: Error loading sessions:", error);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    // Navigate directly to generative with session
    navigate("/app/generative", { 
      state: { 
        selectedSessionId: sessionId,
        selectedTaskName: taskName,
        selectedDisplayName: taskDisplayName
      } 
    });
  };

  const handleNewSessionButton = () => {
    // Navigate to generative with no session selected
    navigate("/app/generative");
  };

  const handleSessionDelete = async (id) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    await removeSession(id);
  };

  const handleRowSelectionModelChange = (newSelection) => {
    setRowSelectionModel(newSelection);
  };

  const handleDocumentChange = () => {
    setDocumentRefreshTrigger((prev) => prev + 1);
  };

  return (
    <Box height="calc(100vh - 74px)" width="100%" display="flex">
      <Box width="20%">
        <SessionBar
          sessions={sessions}
          handleSessionClick={handleSessionClick}
          handleNewSessionButton={handleNewSessionButton}
          handleSessionDelete={handleSessionDelete}
          stepIndex={0}
          showSearch={false}
        />
      </Box>

      <Box width="60%">
        <CenterBox>
            <RAGBreadcrumbs />
            <Typography variant="h5" component="h1">
              RAG Prompts
            </Typography>
            <Typography variant="subtitle1" component="p" sx={{ mb: 2 }}>
              Manage prompts for your RAG sessions: view all available prompts and create new ones to improve your AI interactions.
            </Typography>

            <PromptSelectionTable
              showTableTitle={false}
              loading={false}
              rowSelectionModel={rowSelectionModel}
              onRowSelectionModelChange={handleRowSelectionModelChange}
            />
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
          <RAGDocumentsPanel
            selectedSessionId={null}
            isRagChatActive={false}
            onDocumentChange={handleDocumentChange}
          />
        </Box>
      </Box>
    </Box>
  );
}

export default RAGPromptsPage;