import { Box } from "@mui/material";
import { useEffect } from "react";
import React from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import { getSessions } from "../../api/session";
import { getGenerativeTask } from "../../api/generativeTask";

export default function Generative() {
  const [sessions, setSessions] = React.useState([]);

  const [task, setTask] = React.useState([]);

  useEffect(() => {
    getSessions().then(setSessions);
    getGenerativeTask().then(setTask); // Suponiendo que tienes este estado
  }, []);

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
      <SessionBar sessions={sessions} />
      <MainGenerativeBox>
        <SelectTaskMenu task={task} />
      </MainGenerativeBox>
    </Box>
  );
}
