import { Box, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSession, setSelectedSession] = useState(null);

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
          <SelectTaskMenu goToNextStep={() => setStepIndex(1)}/>
        ) : stepIndex === 1 ? (
          <Box>Second step: select a model and display hiperparameters</Box>
        ) : (
          (stepIndex) => (2 ? <Typography>Not a valid step</Typography> : null)
        )}
      </MainGenerativeBox>
      <Box
        width={"502px"}
        height={"auto"}
        borderRadius={2}
        p={2}
        bgcolor={"#151521"}
      ></Box>
    </Box>
  );
}
