import React from "react";
import { Box, Typography, Button } from "@mui/material";

export default function TaskBox({ taskName, description }) {
  return (
    <Button
      sx={{
        width: "300px",
        minHeight: "40px",
        height: "auto",
        display: "flex",
        justifyContent: "center",
        textTransform: "none",
        backgroundColor: "#4d4d4d",
        "&:hover": {
          backgroundColor: "#3a3a3a",
        },
      }}
      borderRadius={1}
      p={0.5}
      variant="contained"
    >
      <Box
        display={"flex"}
        flexDirection={"column"}
        alignItems={"center"}
        justifyContent={"center"}
        gap={0.5}
        p={2}
      >
        <Typography
          variant="h1"
          sx={{
            fontSize: "16px",
            whiteSpace: "normal",
            wordBreak: "break-word",
            fontWeight: "bold",
          }}
        >
          {taskName}
        </Typography>

        <Typography
          variant="h1"
          sx={{
            fontSize: "16px",
            whiteSpace: "normal",
            wordBreak: "break-word",
          }}
        >
          {description}
        </Typography>
      </Box>
    </Button>
  );
}
