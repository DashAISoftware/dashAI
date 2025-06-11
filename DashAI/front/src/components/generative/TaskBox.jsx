import React from "react";
import { Box, Typography, Button, Paper, useMediaQuery, useTheme } from "@mui/material";

export default function TaskBox({ taskName, description, onClick }) {
  const theme = useTheme();
  const matches = useMediaQuery(theme.breakpoints.up("md"));

  return (
    <Button
      onClick={onClick}
      sx={{
        p: 0,
        m: 0,
        width: "100%",
        height: "128px",
        textAlign: "left",
        textTransform: "none",
        borderRadius: 2,
      }}
    >
      <Paper
        elevation={2}
        sx={{
          p: 2,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: matches ? "row" : "column",
          alignItems: "center",
          justifyContent: matches ? "space-between" : "center",
          textAlign: matches ? "left" : "center",
        }}
      >
        <Box
          sx={{
            width: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-evenly",
            alignItems: matches ? "flex-start" : "center",
            gap: 1,
          }}
        >
          <Typography variant="h6" sx={{ mb: 1 }}>
            {taskName}
          </Typography>
          <Typography variant="caption" component="p">
            {description}
          </Typography>
        </Box>
      </Paper>
    </Button>
  );
}
