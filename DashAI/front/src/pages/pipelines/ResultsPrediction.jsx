import React, { useState } from "react";
import { Box, Typography, Paper, Stack, Button } from "@mui/material";
import DownloadPrediction from "../../components/predictions/DownloadPrediction";
import EditPredictionModal from "../../components/predictions/EditPredictionModal";
import DeleteItemModal from "../../components/custom/DeleteItemModal";
import PredictionSummaryModal from "./ResultsPredictionModal";

function PipelineResultsPrediction({ prediction }) {

  const [openSummary, setOpenSummary] = useState(false);
  const pred_name = prediction

  return (
    <Paper sx={{ p: 4, my: 2 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center">
        <Typography variant="h6">{pred_name}</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" size="small" onClick={() => setOpenSummary(true)}>
            Summary
          </Button>
        </Stack>
      </Box>

      {openSummary && (
        <PredictionSummaryModal
          predictName={pred_name}
          open={openSummary}
          onClose={() => setOpenSummary(false)}
        />
      )}
    </Paper>
  );
}

export default PipelineResultsPrediction;
