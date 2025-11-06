import { Box, Typography } from "@mui/material";
import { useState, useEffect } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import DocumentsBar from "../../components/generative/RAG/DocumentsBar";

import RAGHomePage from "./RAG/RAGHomePage";

import { getSessions, removeSession } from "../../api/session";
import JobQueueWidget from "../../components/jobs/JobQueueWidget";

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  // TODO: Combine selectedTaskName and selectedDisplayName into a single selectedTask State
  const [selectedTaskName, setSelectedTaskName] = useState("");
  const [selectedDisplayName, setSelectedDisplayName] = useState("");
  const [sessions, setSessions] = useState([]);
  const [paramsVersion, setParamsVersion] = useState(0);

  const isRAGTask = () => selectedTaskName === "RAGTask";

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    setSelectedTaskName(taskName);
    setSelectedSessionId(sessionId);
    setSelectedDisplayName(taskDisplayName);
  };

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
  };

  const onParamsUpdate = (newParams) => {
    setParamsVersion((prev) => prev + 1);
  };

  useEffect(() => {
    getSessions().then((data) => {
      setSessions(data);
    });
  }, []);

  const handleAddSession = (session) => {
    setSessions((prevSessions) => [session, ...prevSessions]);
  };

  const handleSessionDelete = (id) => {
    if (id === selectedSessionId) {
      setSelectedSessionId(null);
      setStepIndex(0);
      setSelectedTaskName("");
    }

    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id),
    );

    removeSession(id);
  };

  return (
    <Box height="calc(100vh - 74px)" width="100%" p={1.5} pb={1} display="flex">
      <Box width="22%" mr={1}>
        <SessionBar
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          handleSessionClick={handleSessionClick}
          handleNewSessionButton={handleNewSessionButton}
          handleSessionDelete={handleSessionDelete}
          stepIndex={stepIndex}
        />
      </Box>

      <Box width="56%" mr={1}>
        <MainGenerativeBox>
          {selectedSessionId ? (
            <GenerativeChat
              sessionId={selectedSessionId}
              taskName={selectedTaskName}
              paramsVersion={paramsVersion}
            />
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
        </MainGenerativeBox>
      </Box>

      <Box width="22%">
        <Box
          width="100%"
          height="100%"
          sx={{ backgroundColor: "background.box", borderRadius: 2 }}
        >
          {selectedSessionId ? (
            isRAGTask() ? (
              <DocumentsBar
                selectedSessionId={selectedSessionId}
                taskName={selectedTaskName}
              />
            ) : (
              <ParamsBar
                selectedSessionId={selectedSessionId}
                onParamsUpdate={onParamsUpdate}
                taskName={selectedTaskName}
              />
            )
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
