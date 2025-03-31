import { Box } from "@mui/material";
import { useEffect } from "react";
import React from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import TaskBox from "../../components/generative/TaskBox";
import { getSessions } from "../../api/session";

export default function Generative() {
  const [sessions, setSessions] = React.useState([]);

  useEffect(() => {
    getSessions().then((data) => {
      setSessions(data);
    });
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
      <MainGenerativeBox></MainGenerativeBox>
    </Box>
  );
}
