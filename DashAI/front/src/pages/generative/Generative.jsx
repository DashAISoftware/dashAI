import { Box } from "@mui/material";
import { useEffect, useState } from "react";
import SessionBar from "../../components/generative/SessionBar";
import MainGenerativeBox from "../../components/generative/MainGenerativeBox";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import { getGenerativeTask } from "../../api/generativeTask";

export default function Generative() {
  const [task, setTask] = useState([]);

  useEffect(() => {
    getGenerativeTask().then(setTask);
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
      <SessionBar />
      <MainGenerativeBox>
        <SelectTaskMenu task={task} />
      </MainGenerativeBox>
    </Box>
  );
}
