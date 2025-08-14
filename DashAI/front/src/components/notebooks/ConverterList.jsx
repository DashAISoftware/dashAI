import React from "react";
import { Box, Button, Typography } from "@mui/material";

export default function ConverterList({
  converters,
  hoveredTool,
  setHoveredTool,
  handleConverterClick,
}) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {converters.length === 0 ? (
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            textAlign: "center",
            py: 2,
          }}
        >
          No converters found matching your search.
        </Typography>
      ) : (
        converters.map((converter) => (
          <Button
            key={converter.type}
            variant="contained"
            sx={{
              bgcolor: hoveredTool === converter.type ? "#444" : "#333",
              color: "white",
              justifyContent: "flex-start",
              textTransform: "none",
              fontWeight: "normal",
              py: 1.5,
              "&:hover": { bgcolor: "#444" },
            }}
            onMouseEnter={() => setHoveredTool(converter)}
            onMouseLeave={() => setHoveredTool(null)}
            onClick={() => handleConverterClick(converter.type, converter.name)}
          >
            {converter.name}
          </Button>
        ))
      )}
    </Box>
  );
}
