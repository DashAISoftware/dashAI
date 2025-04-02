import { Box, Typography, Autocomplete, TextField } from "@mui/material";
import { useEffect, useState } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import { getRelatedComponents } from "../../api/generativeTask";

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedTaskName, setSelectedTaskName] = useState("");
  const [relatedComponents, setRelatedComponents] = useState([]);

  useEffect(() => {
    if (!selectedTaskName) return;

    getRelatedComponents(selectedTaskName).then(setRelatedComponents);
  }, [selectedTaskName]);

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
          <Box>
            Select a model from the list:
            <Autocomplete
              disablePortal
              options={relatedComponents.map((t) => t.name)}
              sx={{ m: 5 }}
              renderInput={(params) => <TextField {...params} label="Model" />}
            />
          </Box>
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
