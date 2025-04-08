import { Box, Typography, Autocomplete, TextField } from "@mui/material";
import { useState } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedTaskName, setSelectedTaskName] = useState("");

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
      <SessionBar />
      <MainGenerativeBox>
        {selectedSession ? (
          <GenerativeChat />
        ) : stepIndex === 0 ? (
          <SelectTaskMenu
            goToNextStep={(taskName) => {
              setSelectedTaskName(taskName);
              setStepIndex(1);
            }}
          />
        ) : stepIndex === 1 ? (
          <SelectModelMenu selectedTaskName={selectedTaskName} />
        ) : (
          (stepIndex) => (2 ? <Typography>Not a valid step</Typography> : null)
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
