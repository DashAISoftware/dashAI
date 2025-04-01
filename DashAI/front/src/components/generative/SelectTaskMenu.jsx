import React from "react";
import { Box, Typography } from "@mui/material";
import TaskBox from "../../components/generative/TaskBox";
import IconAvatar from "../../components/generative/IconAvatar";
import SearchBar from "../../components/generative/SearchBar";

export default function SelectTaskMenu({ task }) {
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
          margin: 5,
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
        sx={{ margin: 5 }}
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
            taskName={task.task_name}
            description={task.description}
          />
        ))}
      </Box>
      {/* Search Bar */}
      <Box sx={{ m: 5 }}>
        <SearchBar placeholder={"Task"} />
      </Box>
    </Box>
  );
}
