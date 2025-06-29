import { Box, Typography } from "@mui/material";
import { useState, useEffect } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";

import RAGHomePage from "./RAG/RAGHomePage";

import { getSessions, removeSession } from "../../api/session";

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedTaskName, setSelectedTaskName] = useState("");
  const [sessions, setSessions] = useState([]);
  const [paramsVersion, setParamsVersion] = useState(0);

  const isRAGTask = () => selectedTaskName === "RAGTask";

  const handleSessionClick = (sessionId, taskName) => {
    console.log("[handleSessionClick]", { sessionId, taskName });
    setSelectedTaskName(taskName);
    setSelectedSessionId(sessionId);
  };

  const handleNewSessionButton = () => {
    console.log("[handleNewSessionButton]");
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
  };

  const onParamsUpdate = (newParams) => {
    console.log("[onParamsUpdate]", newParams);
    setParamsVersion((prev) => prev + 1);
  };

  useEffect(() => {
    getSessions().then((data) => {
      console.log("[getSessions]", data);
      setSessions(data);
    });
  }, []);

  const handleAddSession = (session) => {
    console.log("[handleAddSession]", session);
    setSessions((prevSessions) => [session, ...prevSessions]);
  };

  const handleSessionDelete = (id) => {
    console.log("[handleSessionDelete]", id);
    if (id === selectedSessionId) {
      setSelectedSessionId(null);
      setStepIndex(0);
      setSelectedTaskName("");
    }

    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id)
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
            isRAGTask() ? (
              <GenerativeChat
                sessionId={selectedSessionId}
                taskName={selectedTaskName}
                paramsVersion={paramsVersion}
              />
              ) : (
              <GenerativeChat
                sessionId={selectedSessionId}
                taskName={selectedTaskName}
                paramsVersion={paramsVersion}
              />
              )
            ) : stepIndex === 0 ? (
              <SelectTaskMenu
                goToNextStep={(taskName) => {
                  console.log("[SelectTaskMenu] task selected:", taskName);
                  setSelectedTaskName(taskName);
                  setStepIndex(1);
                }}
              />
              ) : isRAGTask() ? (
                <RAGHomePage
                  handleAddSession={handleAddSession}
                  selectedTaskName={selectedTaskName}
                  setSelectedSessionId={setSelectedSessionId}
                />
              ) : (
                <SelectModelMenu
                  handleAddSession={handleAddSession}
                  selectedTaskName={selectedTaskName}
                  setSelectedSessionId={setSelectedSessionId}
                />
              )
          }
        </MainGenerativeBox>
      </Box>
      
      {!isRAGTask() && (
      <Box width="22%">
        <Box
          width="100%"
          height="100%"
          sx={{ backgroundColor: "background.box", borderRadius: 2 }}
        >
          {!selectedSessionId ?
            (
              <ParamsBar
                selectedSessionId={selectedSessionId}
                onParamsUpdate={onParamsUpdate}
                taskName={selectedTaskName}
              />
            ): null}
        </Box>
      </Box>
        )
        }
    </Box>
  );
}
