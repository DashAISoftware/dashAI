import React from "react";
import { Box, Divider, Paper, Typography } from "@mui/material";

export default function MetricsCard({ title, metrics }) {
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
            <Typography variant="body2" color="text.secondary">
              {key}:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {value[0].toFixed(4)}
            </Typography>
          </Box>
        ))
      ) : (
        <Typography variant="body2" color="text.secondary">
          No metrics available
        </Typography>
      )}
    </Paper>
  );
}
