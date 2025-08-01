import React from "react";
import { Paper } from "@mui/material";
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
