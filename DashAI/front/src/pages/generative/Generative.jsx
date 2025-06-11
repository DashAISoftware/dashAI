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
  const [paramsVersion, setParamsVersion] = useState(0);

  const handleSessionClick = (sessionId, taskName) => {
    setSelectedTaskName(taskName);
    setSelectedSessionId(sessionId);
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
    }

    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id),
    );

    removeSession(id);
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
      overflow={"hidden"}
    >
      <SessionBar
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        handleSessionClick={handleSessionClick}
        handleNewSessionButton={handleNewSessionButton}
        handleSessionDelete={handleSessionDelete}
        stepIndex={stepIndex}
      />
      <MainGenerativeBox>
        {selectedSessionId ? (
          <GenerativeChat
            sessionId={selectedSessionId}
            taskName={selectedTaskName}
            paramsVersion={paramsVersion}
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
        width={"600px"}
        maxWidth={"600px"}
        height={"100%"}
        borderRadius={2}
        bgcolor={"background.box"}
        //p={2}
      >
        {selectedSessionId ? (
          <ParamsBar
            selectedSessionId={selectedSessionId}
            onParamsUpdate={onParamsUpdate}
            taskName={selectedTaskName}
          />
        ) : null}
      </Box>
    </Box>
  );
}
