import React, { useState, useRef, useEffect, useCallback } from "react";
import { Box } from "@mui/material";
import NotebookView from "./NotebookView";
import DatasetPreviewNotebook from "./DatasetPreviewNotebook";
import JobQueueWidget from "../../jobs/JobQueueWidget";


export default function NotebookVisualization({
  notebook,
  handleAddDatasetFromNotebook,
  existingDatasets = [],
}) {
  const [topHeight, setTopHeight] = useState(() => {
    return window.innerHeight * 0.4;
  });
  const [isAccordionExpanded, setIsAccordionExpanded] = useState(true);
  const [isToggling, setIsToggling] = useState(false); 
  const isResizing = useRef(false);

  const handleMouseDown = () => {
    isResizing.current = true;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
  };

  const handleMouseMove = useCallback((e) => {
    if (!isResizing.current) return;

    const container = document.querySelector('[data-notebook-container]');
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const mouseY = e.clientY;
    const newHeight = mouseY - rect.top;

    const minHeight = 200;
    const maxHeight = rect.height * 0.7;
    const clampedHeight = Math.max(minHeight, Math.min(maxHeight, newHeight));
    setTopHeight(clampedHeight);
  }, []);

  const handleMouseUp = useCallback(() => {
    isResizing.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, []);

  const handleAccordionChange = (expanded) => {
    setIsToggling(true);
    setIsAccordionExpanded(expanded);
    setTimeout(() => setIsToggling(false), 300); 
  };

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const actualTopHeight = isAccordionExpanded ? topHeight : 64;

  return (
    <>
      <Box 
        sx={{ display: "flex", flexDirection: "column", height: "100%" }}
        data-notebook-container
      >
        {/* Dataset View  */}
        <Box 
          sx={{ 
            flexShrink: 0, 
            height: actualTopHeight, 
            mb: 2,
            transition: isToggling 
              ? "height 0.3s cubic-bezier(0.4, 0, 0.2, 1)" 
              : "none",
            overflow: "hidden",
          }}
        >
          <DatasetPreviewNotebook
            notebook={notebook}
            handleAddDatasetFromNotebook={handleAddDatasetFromNotebook}
            existingDatasets={existingDatasets}
            height={topHeight}
            onAccordionChange={handleAccordionChange}
          />
        </Box>

        {/* Resize Handle */}
        {isAccordionExpanded && (
          <Box
            onMouseDown={handleMouseDown}
            sx={{
              height: "8px",
              cursor: "row-resize",
              bgcolor: "rgba(255, 255, 255, 0.05)",
              borderTop: "1px solid rgba(255, 255, 255, 0.1)",
              borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
              transition: "all 0.2s ease",
              "&:hover": {
                bgcolor: "primary.main",
                opacity: 0.7,
              },
              zIndex: 10,
              flexShrink: 0,
              mb: 2,
            }}
          />
        )}

        {/* Notebook view */}
        <Box sx={{ flexGrow: 1, minHeight: 200, overflow: "auto" }}>
          <NotebookView notebook={notebook} />
        </Box>
      </Box>
      <JobQueueWidget />
    </>
  );
}
