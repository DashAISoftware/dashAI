import React from "react";
import { Box, Typography, Button } from "@mui/material";

export default function TaskBox({ taskName, description, onClick }) {
  return (
    <Button
      onClick={onClick}
      sx={{
        width: "300px",
        minHeight: "40px",
        color: "white",
        height: "auto",
        display: "flex",
        justifyContent: "center",
        textTransform: "none",
        backgroundColor: "#374151",
        "&:hover": {
          backgroundColor: "#475569",
        },
        borderRadius: 3,
      }}
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
            fontSize: "14px",
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
