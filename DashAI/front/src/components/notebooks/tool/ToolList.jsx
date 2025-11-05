import React, { useState } from "react";
import { Box } from "@mui/material";
import ToolListItem from "./ToolListItem";
import ConfigureToolModal from "./ConfigureToolModal";
import { useTourContext } from "../../tour/TourProvider";

export default function ToolList({ tools, notebook, FormComponent }) {
  const [open, setOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const tourContext = useTourContext();

  const handleToolClick = (tool) => {
    setSelectedTool(tool);
    setOpen(true);

    if (tourContext && tourContext.run) {
      const shouldAdvance =
        tool.name === "HistogramPlotExplorer" ||
        tool.name === "LabelEncoder" ||
        tool.name === "NanRemover";

      if (shouldAdvance) {
        setTimeout(() => {
          tourContext.nextStep();
        }, 500);
      }
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        minWidth: 0,
      }}
    >
      {tools.map((item) => (
        <ToolListItem
          key={item.name}
          tool={item}
          disabled={item.disabled}
          onClick={() => handleToolClick(item)}
        />
      ))}
      {selectedTool && (
        <ConfigureToolModal
          open={open}
          handleClose={() => {
            setOpen(false);
            setSelectedTool(null);
          }}
          tool={selectedTool}
          notebook={notebook}
          FormSection={FormComponent}
        />
      )}
    </Box>
  );
}
