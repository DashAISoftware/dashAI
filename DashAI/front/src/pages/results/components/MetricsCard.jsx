import React from "react";
import { Box, Divider, Paper, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function MetricsCard({ title, metrics }) {
  const theme = useTheme();

  return (
    <Paper elevation={2} sx={{ p: 2, height: "100%" }}>
      <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
        {title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      {metrics && Object.keys(metrics).length > 0 ? (
        Object.entries(metrics).map(([key, value]) => (
          <Box
            key={key}
            sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
          >
            <Typography
              variant="body2"
              sx={{ color: theme.palette.text.secondary }}
            >
              {key}:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {value.toFixed(4)}
            </Typography>
          </Box>
        ))
      ) : (
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.secondary }}
        >
          No metrics available
        </Typography>
      )}
    </Paper>
  );
}
