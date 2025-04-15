import { Box } from "@mui/material";
import { useState } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedTaskName, setSelectedTaskName] = useState("");

  const handleSessionClick = (sessionId, taskName) => {
    setSelectedSessionId(sessionId);
    setSelectedTaskName(taskName);
  };

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
  };

  return (
    <Box
      display={"flex"}
      style={{ position: "absolute" }}
      justifyContent={"flex-start"}
      gap={3}
      height={"90%"}
      flexGrow={1}
      width={"100%"}
      p={1.5}
      alignItems={"stretch"}
    >
      <SessionBar
        selectedSessionId={selectedSessionId}
        handleSessionClick={handleSessionClick}
        handleNewSessionButton={handleNewSessionButton}
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
            selectedTaskName={selectedTaskName}
            setSelectedSessionId={setSelectedSessionId}
          />
        )}
      </MainGenerativeBox>
      <Box
        width={"502px"}
        height={"auto"}
        borderRadius={2}
        p={2}
        bgcolor={"#030712"}
      ></Box>
    </Box>
  );
}
