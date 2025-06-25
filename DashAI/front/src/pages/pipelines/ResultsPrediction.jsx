import React, { useState } from "react";
import { Box, Typography, Paper, Tooltip, IconButton } from "@mui/material";
import { Search } from "@mui/icons-material";
import PredictionSummary from "./ResultsPredictionModal";

function PipelineResultsPrediction({ prediction }) {
  const pred_name = prediction;

  return (
    <Paper sx={{ width: "100%" }}>
      <PredictionSummary predictName={pred_name} />
    </Paper>
  );
}

export default PipelineResultsPrediction;
