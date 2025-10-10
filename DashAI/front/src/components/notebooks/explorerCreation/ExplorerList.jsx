import React, { useState } from "react";
import { Box, Typography } from "@mui/material";
import ConfigureToolModal from "../ConfigureToolModal";
import FormExplorerSection from "./FormExplorerSection";
import ToolListItem from "./ToolListItem";

export default function ExplorerList({ explorers }) {
  const [open, setOpen] = useState(false);
  const [selectedExplorer, setSelectedExplorer] = useState(null);

  const handleExplorerClick = (explorer) => {
    setSelectedExplorer(explorer);
    setOpen(true);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column" }}>
      {explorers.length === 0 ? (
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            textAlign: "center",
            py: 2,
          }}
        >
          No explorations found matching your search.
        </Typography>
      ) : (
        explorers.map((exploration) => (
          <ToolListItem
            key={exploration.name}
            tool={exploration}
            disabled={exploration.disabled}
            onClick={() => handleExplorerClick(exploration)}
          />
        ))
      )}

      {selectedExplorer && (
        <ConfigureToolModal
          open={open}
          handleClose={() => {
            setOpen(false);
            setSelectedExplorer(null);
          }}
          tool={selectedExplorer}
          notebook={selectedExplorer.notebook}
          FormSection={FormExplorerSection}
        />
      )}
    </Box>
  );
}
