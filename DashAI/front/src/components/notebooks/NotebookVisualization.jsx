import React from "react";
import { Box, Typography, Divider, CircularProgress } from "@mui/material";
import NotebookView from "./NotebookView";
import DatasetPreviewNotebook from "./DatasetPreviewNotebook";

export default function NotebookVisualization({
  notebook,
  handleAddDatasetFromNotebook,
}) {
  return (
    <Box>
      <Box>
        {/* Dataset View */}
        <DatasetPreviewNotebook
          notebook={notebook}
          handleAddDatasetFromNotebook={handleAddDatasetFromNotebook}
        />
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Notebook view */}
      <Box mt={2}>
        <Typography variant="h5" my={2}>
          Analysis Results
        </Typography>
        <NotebookView notebook={notebook} />
      </Box>
    </Box>
  );
}
