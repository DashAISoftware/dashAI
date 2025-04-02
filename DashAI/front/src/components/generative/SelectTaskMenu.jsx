import React from "react";
import { Box, Typography, Autocomplete, TextField } from "@mui/material";
import TaskBox from "../../components/generative/TaskBox";
import IconAvatar from "../../components/generative/IconAvatar";

const top100Films = [
  { label: "The Shawshank Redemption", year: 1994 },
  { label: "The Godfather", year: 1972 },
  { label: "The Godfather: Part II", year: 1974 },
  { label: "Pulp Fiction", year: 1994 },
  { label: "Schindler's List", year: 1993 },
  { label: "Raging Bull", year: 1980 },
  { label: "Casablanca", year: 1942 },
  { label: "Citizen Kane", year: 1941 },
];

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
