import React from "react";
import { Paper, Typography } from "@mui/material";

export const StatBox = ({ label, value }) => (
  <Paper
    elevation={1}
    sx={{
      p: 2,
      textAlign: "center",
      borderRadius: 2,
      bgcolor: "#363636",
      width: "200px",
    }}
  >
    <Typography variant="h5" fontWeight="bold" color="text.primary">
      {value}
    </Typography>
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
  </Paper>
);
