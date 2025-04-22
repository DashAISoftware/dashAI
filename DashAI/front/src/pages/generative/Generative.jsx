import { Box } from "@mui/material";
import { useState } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import { getSessions, removeSession } from "../../api/session";
import { useEffect } from "react";

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedTaskName, setSelectedTaskName] = useState("");
  const [sessions, setSessions] = useState([]);

  const handleSessionClick = (sessionId, taskName) => {
    setSelectedSessionId(sessionId);
    setSelectedTaskName(taskName);
  };

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
  };

  useEffect(() => {
    getSessions().then((data) => {
      setSessions(data);
    });
  }, []);

  const handleAddSession = (session) => {
    setSessions((prevSessions) => [...prevSessions, session]);
  };

  const handleSessionDelete = (id) => {
    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id),
    );
    removeSession(id).then(() => {
      console.log("Session deleted", id);
    });
    setSelectedSessionId(null);
    setStepIndex(0);
  };

  return (
    <Box
      display={"flex"}
      style={{ position: "absolute" }}
      justifyContent={"flex-start"}
      gap={3}
      height={"calc(100vh - 74px)"}
      flexGrow={1}
      width={"100%"}
      p={1.5}
      alignItems={"stretch"}
    >
      <SessionBar
        sessions={sessions}
        setSessions={() => setSessions()}
        selectedSessionId={selectedSessionId}
        handleSessionClick={handleSessionClick}
        handleNewSessionButton={handleNewSessionButton}
        handleSessionDelete={handleSessionDelete}
      />
      <MainGenerativeBox>
        {selectedSessionId ? (
          <GenerativeChat
            sessionId={selectedSessionId}
            taskName={selectedTaskName}
          />
        ) : stepIndex === 0 ? (
          <SelectTaskMenu
            goToNextStep={(taskName) => {
              setSelectedTaskName(taskName);
              setStepIndex(1);
            }}
          />
        ) : (
          <SelectModelMenu
            handleAddSession={handleAddSession}
            selectedTaskName={selectedTaskName}
            setSelectedSessionId={setSelectedSessionId}
          />
        )}
      </MainGenerativeBox>
      <Box
        width={"502px"}
        height={"100%"}
        borderRadius={2}
        p={2}
        bgcolor={"#030712"}
      >
        {selectedSessionId ? (
          <ParamsBar selectedSessionId={selectedSessionId} />
        ) : null}
      </Box>
    </Box>
  );
}
