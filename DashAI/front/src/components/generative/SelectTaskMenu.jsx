import React from "react";
import { Box, Typography, Autocomplete, TextField } from "@mui/material";
import TaskBox from "../../components/generative/TaskBox";
import IconAvatar from "../../components/generative/IconAvatar";
import { useEffect, useState } from "react";
import { getGenerativeTask } from "../../api/generativeTask";

export default function SelectTaskMenu({ goToNextStep }) {
  const [task, setTask] = useState([]);

  useEffect(() => {
    getGenerativeTask().then(setTask);
  }, []);

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
    >
      <Typography
        variant="h1"
        sx={{
          fontFamily: "Roboto",
          fontSize: "16px",
          whiteSpace: "normal",
          wordBreak: "break-word",
          ml: 5,
          mt: 1,
          mr: 5,
          mb: 5,
        }}
      >
        Select a generative task
      </Typography>
      <Box sx={{ ml: 5 }}>
        <IconAvatar src="/dai_circle.png" size={32} />{" "}
      </Box>
      <Box
        display={"flex"}
        flexDirection={"column"}
        alignItems={"flex-start"}
        justifyContent={"center"}
        gap={1}
        sx={{ mt: 2, mb: 5, ml: 5, mr: 5 }}
      >
        <Typography
          variant="h1"
          sx={{
            fontSize: "24px",
            whiteSpace: "normal",
            wordBreak: "break-word",
          }}
        >
          Hello
        </Typography>

        <Typography
          variant="h1"
          sx={{
            fontSize: "24px",
            whiteSpace: "normal",
            wordBreak: "break-word",
            color: "#aba5a5",
          }}
        >
          Select a generative task to start
        </Typography>
      </Box>
      <Box
        display={"flex"}
        justifyContent={"space-evenly"}
        alignItems={"stretch"}
        width={"100%"}
      >
        {task.map((task, index) => (
          <TaskBox
            key={index}
            taskName={task.display_name}
            description={task.description}
            onClick={() => goToNextStep(task.name)}
          />
        ))}
      </Box>
      {/* Search Bar */}
      <Autocomplete
        disablePortal
        options={task.map((t) => t.display_name)}
        sx={{ m: 5 }}
        renderInput={(params) => <TextField {...params} label="Task" />}
      />
    </Box>
  );
}
