import React, { useState } from "react";
import { Box } from "@mui/material";
import ToolListItem from "./ToolListItem";
import ConfigureToolModal from "./ConfigureToolModal";

export default function ToolList({ tools, notebook, FormComponent }) {
  const [open, setOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);

  const handleToolClick = (tool) => {
    setSelectedTool(tool);
    setOpen(true);
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
