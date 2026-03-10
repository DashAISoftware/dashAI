import React from "react";
import { Paper, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export const StatBox = ({ label, value }) => {
  const theme = useTheme();
  return (
    <Paper
      elevation={1}
      sx={{
        p: 2,
        textAlign: "center",
        borderRadius: 2,
        bgcolor: theme.palette.ui.panelMedium,
        width: "200px",
      }}
    >
      <Typography
        variant="h5"
        fontWeight="bold"
        sx={{ color: theme.palette.text.primary }}
      >
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Paper>
  );
};
