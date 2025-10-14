import React, { useState } from "react";
import { Box } from "@mui/material";
import ToolGridItem from "./ToolGridItem";
import ConfigureToolModal from "./ConfigureToolModal";

export default function ToolGrid({ tools, notebook, FormComponent }) {
  const [open, setOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);

  const handleToolClick = (tool) => {
    setSelectedTool(tool);
    setOpen(true);
  };
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: 1.5,
      }}
    >
      {tools.map((item) => (
        <ToolGridItem
          key={item.id}
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
