import { Box, Typography } from "@mui/material";
import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import DocumentsBar from "../../components/generative/RAG/DocumentsBar";
import RAGSessionSummary from "../../components/generative/RAG/RAGSessionSummary";

import RAGHomePage from "./RAG/RAGHomePage";

import { getSessions, removeSession } from "../../api/session";
import JobQueueWidget from "../../components/jobs/JobQueueWidget";
import CenterBox from "../../components/threeSectionLayout/CenterBox";

export default function Generative() {
  const location = useLocation();
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState(
    location.state?.selectedSessionId || null
  );
  // TODO: Combine selectedTaskName and selectedDisplayName into a single selectedTask State
  const [selectedTaskName, setSelectedTaskName] = useState("");
  const [selectedDisplayName, setSelectedDisplayName] = useState("");
  const [sessions, setSessions] = useState([]);
  const [paramsVersion, setParamsVersion] = useState(0);
  const [showRAGSummary, setShowRAGSummary] = useState(false);
  const [documentRefreshTrigger, setDocumentRefreshTrigger] = useState(0);

  const isRAGTask = () => selectedTaskName === "RAGTask";

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    setSelectedTaskName(taskName);
    setSelectedSessionId(sessionId);
    setSelectedDisplayName(taskDisplayName);
    
    // Show RAG summary for RAG tasks, chat for others
    setShowRAGSummary(taskName === "RAGTask");
  };

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
    setShowRAGSummary(false);
  };

  const handleStartRAGChat = () => {
    setShowRAGSummary(false);
  };

  const onParamsUpdate = (newParams) => {
    setParamsVersion((prev) => prev + 1);
  };

  const handleDocumentChange = () => {
    setDocumentRefreshTrigger((prev) => prev + 1);
  };

  useEffect(() => {
    getSessions().then((data) => {
      setSessions(data);
    });
  }, []);

  // Handle navigation from RAG pages
  useEffect(() => {
    if (location.state?.selectedSessionId) {
      setSelectedSessionId(location.state.selectedSessionId);
      
      // Use the task info from navigation state if available, otherwise find from session
      if (location.state.selectedTaskName && location.state.selectedDisplayName) {
        setSelectedTaskName(location.state.selectedTaskName);
        setSelectedDisplayName(location.state.selectedDisplayName);
        setShowRAGSummary(location.state.selectedTaskName === "RAGTask");
      } else {
        const session = sessions.find(s => s.id === location.state.selectedSessionId);
        if (session) {
          setSelectedTaskName(session.task_name);
          setSelectedDisplayName(session.task_name); // Map this if needed
          setShowRAGSummary(session.task_name === "RAGTask");
        }
      }
      
      // Clear the navigation state to prevent re-triggering
      window.history.replaceState(null, '', window.location.pathname);
    }
  }, [location.state, sessions]);

  const handleAddSession = (session) => {
    setSessions((prevSessions) => [session, ...prevSessions]);
    
    // Auto-select the new session and show RAG summary if it's a RAG task
    setSelectedSessionId(session.id);
    setSelectedTaskName(session.task_name);
    setSelectedDisplayName(session.display_name || session.task_name);
    setShowRAGSummary(session.task_name === "RAGTask");
  };

  const handleSessionDelete = (id) => {
    if (id === selectedSessionId) {
      setSelectedSessionId(null);
      setStepIndex(0);
      setSelectedTaskName("");
      setShowRAGSummary(false);
    }

    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id),
    );

    removeSession(id);
  };

  const handleNavigateToGenerative = () => {
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
    setSelectedDisplayName("");
    setShowRAGSummary(false);
  };

  return (
    <Box height="calc(100vh - 74px)" width="100%" display="flex">
      <Box width="20%">
        <SessionBar
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          handleSessionClick={handleSessionClick}
          handleNewSessionButton={handleNewSessionButton}
          handleSessionDelete={handleSessionDelete}
          stepIndex={stepIndex}
        />
      </Box>
      <Box width="60%">
        <CenterBox>
          {selectedSessionId ? (
            showRAGSummary && isRAGTask() ? (
              <RAGSessionSummary
                sessionId={selectedSessionId}
                onStartChat={handleStartRAGChat}
                onNavigateToGenerative={handleNavigateToGenerative}
              />
            ) : (
              <GenerativeChat
                sessionId={selectedSessionId}
                taskName={selectedTaskName}
                paramsVersion={paramsVersion}
                onNavigateToGenerative={handleNavigateToGenerative}
              />
            )
          ) : stepIndex === 0 ? (
            <SelectTaskMenu
              goToNextStep={(taskName, displayName) => {
                setSelectedDisplayName(displayName);
                setSelectedTaskName(taskName);
                setStepIndex(1);
              }}
            />
          ) : isRAGTask() ? (
            <RAGHomePage
              onSessionCreated={handleAddSession}
              onSessionSelect={setSelectedSessionId}
              sessions={sessions}
              setSessions={setSessions}
              onNavigateToGenerative={handleNavigateToGenerative}
            />
          ) : (
            <SelectModelMenu
              goToBackStep={() => setStepIndex(0)}
              handleAddSession={handleAddSession}
              selectedTaskName={selectedTaskName}
              selectedDisplayName={selectedDisplayName}
              setSelectedSessionId={setSelectedSessionId}
              existingSessions={sessions}
            />
          )}
        </CenterBox>
      </Box>

      <Box width="22%" sx={{ flexShrink: 0, flexGrow: 0 }}>
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
          {console.log("Selected Session ID:", selectedSessionId)}
          {console.log("Selected Task Name:", selectedTaskName)}
          {selectedSessionId && selectedTaskName ? (
            isRAGTask() ? (
              <DocumentsBar
                selectedSessionId={selectedSessionId}
                taskName={selectedTaskName}
                onDocumentChange={handleDocumentChange}
                key={`documents-${selectedSessionId}-${documentRefreshTrigger}`}
              />
            ) : (
              <ParamsBar
                selectedSessionId={selectedSessionId}
                onParamsUpdate={onParamsUpdate}
                taskName={selectedTaskName}
              />
            )
          ) : isRAGTask() && selectedTaskName ? (
            <DocumentsBar
              selectedSessionId={null}
              taskName={selectedTaskName}
              onDocumentChange={handleDocumentChange}
              key={`documents-no-session-${documentRefreshTrigger}`}
            />
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
