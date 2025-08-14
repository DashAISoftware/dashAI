import React from "react";
import { Box, Button, Typography } from "@mui/material";

export default function ExplorerList({
  explorers,
  hoveredTool,
  setHoveredTool,
  handleExplorerClick,
}) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
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
          <Button
            key={exploration.type}
            variant="contained"
            sx={{
              bgcolor: hoveredTool === exploration.type ? "#444" : "#333",
              color: "white",
              justifyContent: "flex-start",
              textTransform: "none",
              fontWeight: "normal",
              py: 1.5,
              "&:hover": { bgcolor: "#444" },
            }}
            onMouseEnter={() => setHoveredTool(exploration)}
            onMouseLeave={() => setHoveredTool(null)}
            onClick={() =>
              handleExplorerClick(exploration.type, exploration.name)
            }
          >
            {exploration.name}
          </Button>
        ))
      )}
    </Box>
  );
}
