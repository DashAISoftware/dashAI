import { useState } from "react";
import { Box, Card, CardContent, Typography, Paper } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import StorageIcon from "@mui/icons-material/Storage";
import CreateIcon from "@mui/icons-material/Create";

function ModeSelector({ predictionMode, setPredictionMode }) {
  const theme = useTheme();

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
        Select Prediction Mode
      </Typography>
      <Typography
        variant="body2"
        sx={{ color: theme.palette.text.secondary, mb: 2 }}
      >
        Choose how you would like to provide input data for the prediction.
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
        <Paper
          elevation={predictionMode === "dataset" ? 3 : 0}
          sx={{
            p: 2,
            cursor: "pointer",
            border: 2,
            borderColor:
              predictionMode === "dataset" ? "primary.main" : "divider",
            bgcolor:
              predictionMode === "dataset"
                ? "primary.light"
                : "background.paper",
            "&:hover": {
              bgcolor:
                predictionMode === "dataset" ? "primary.light" : "action.hover",
            },
          }}
          onClick={() => setPredictionMode("dataset")}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <StorageIcon
              color={predictionMode === "dataset" ? "primary" : "action"}
            />
            <Box>
              <Typography variant="body2" fontWeight={600}>
                Use Existing Dataset
              </Typography>
              <Typography
                variant="caption"
                sx={{ color: theme.palette.text.secondary }}
              >
                Select a dataset from the platform
              </Typography>
            </Box>
          </Box>
        </Paper>
        <Paper
          elevation={predictionMode === "manual" ? 3 : 0}
          sx={{
            p: 2,
            cursor: "pointer",
            border: 2,
            borderColor:
              predictionMode === "manual" ? "primary.main" : "divider",
            bgcolor:
              predictionMode === "manual"
                ? "primary.light"
                : "background.paper",
            "&:hover": {
              bgcolor:
                predictionMode === "manual" ? "primary.light" : "action.hover",
            },
          }}
          onClick={() => setPredictionMode("manual")}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <CreateIcon
              color={predictionMode === "manual" ? "primary" : "action"}
            />
            <Box>
              <Typography variant="body2" fontWeight={600}>
                Manual Prediction
              </Typography>
              <Typography
                variant="caption"
                sx={{ color: theme.palette.text.secondary }}
              >
                Enter values manually
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}

export default ModeSelector;
