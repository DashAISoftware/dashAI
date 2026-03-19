import React, { useState } from "react";
import { Box, Divider } from "@mui/material";
import NotebookView from "./NotebookView";
import DatasetPreviewNotebook from "./DatasetPreviewNotebook";

const EMPTY_ARRAY = [];

export default function NotebookVisualization({
  notebook,
  existingDatasets = EMPTY_ARRAY,
}) {
  const [isAccordionExpanded, setIsAccordionExpanded] = useState(true);

  return (
    <>
      <Box
        sx={{ display: "flex", flexDirection: "column", height: "100%" }}
        data-notebook-container
      >
        {/* Dataset View */}
        <Box sx={{ flexGrow: 0, position: "sticky" }}>
          <DatasetPreviewNotebook
            notebook={notebook}
            existingDatasets={existingDatasets}
            onAccordionChange={setIsAccordionExpanded}
          />
        </Box>

        <Divider sx={{ my: 1, mt: 1 }} />

        {/* Notebook view */}
        <Box sx={{ flexGrow: 1, minHeight: 200, overflow: "auto" }}>
          <NotebookView notebook={notebook} />
        </Box>
      </Box>
    </>
  );
}
