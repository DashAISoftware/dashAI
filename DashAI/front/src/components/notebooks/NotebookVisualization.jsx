import React from "react";
import { Box, Typography, Divider, CircularProgress } from "@mui/material";
import NotebookView from "./NotebookView";
import DatasetPreviewNotebook from "./DatasetPreviewNotebook";

export default function NotebookVisualization({
  notebook,
  handleAddDatasetFromNotebook,
}) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Box sx={{ flexGrow: 0, position: "sticky" }}>
        {/* Dataset View */}
        <DatasetPreviewNotebook
          notebook={notebook}
          handleAddDatasetFromNotebook={handleAddDatasetFromNotebook}
        />
      </Box>

      <Divider sx={{ my: 1, mt: 1 }} />

      {/* Notebook view */}
      <Box mt={2} sx={{ flexGrow: 1, overflow: "auto" }}>
        <Typography variant="h5" mb={1.5}>
          Analysis Results
        </Typography>
        <NotebookView notebook={notebook} />
      </Box>
    </Box>
  );
}
