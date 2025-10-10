import React, { useState } from "react";

import { Box, Typography, Chip } from "@mui/material";
import HoverToolInfo from "./HoverToolInfo";

export default function ToolListItem({ tool, disabled = false, onClick }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [hoveredTool, setHoveredTool] = useState(null);

  const handleMouseEnter = (event, tool) => {
    setAnchorEl(event.currentTarget);
    setHoveredTool(tool);
  };

  const handleMouseLeave = () => {
    setAnchorEl(null);
    setHoveredTool(null);
  };

  return (
    <>
      <Box
        key={tool.id}
        onMouseEnter={(e) => handleMouseEnter(e, tool)}
        onMouseLeave={handleMouseLeave}
        onClick={disabled ? null : onClick}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          p: 1.5,
          bgcolor: "rgb(20, 20, 24)",
          border: "1px solid rgb(39, 39, 42)",
          borderRadius: 1.5,
          cursor: disabled ? "not-allowed" : "pointer",
          transition: "all 0.2s",
          "&:hover": {
            bgcolor: disabled ? "rgb(20, 20, 24)" : "rgb(30, 30, 34)",
            borderColor: disabled ? "rgb(39, 39, 42)" : "rgb(63, 63, 70)",
            transform: disabled ? "none" : "translateX(4px)",
          },
        }}
      >
        {/* Icon */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 36,
            height: 36,
            borderRadius: 1,
            bgcolor: "rgb(63, 63, 70)",
            color: "rgb(250, 250, 250)",
            flexShrink: 0,
          }}
        >
          {tool.icon}
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
            <Typography
              variant="body2"
              sx={{
                color: "rgb(250, 250, 250)",
                fontWeight: 500,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {tool.display_name}
            </Typography>
          </Box>
          <Typography variant="caption" sx={{ color: "rgb(113, 113, 122)" }}>
            {tool.categoryLabel}
          </Typography>
        </Box>

        {/* Preview Thumbnail */}
        <Box
          sx={{
            width: 60,
            height: 40,
            borderRadius: 0.75,
            bgcolor: "rgb(39, 39, 42)",
            border: "1px solid rgb(63, 63, 70)",
            overflow: "hidden",
            flexShrink: 0,
          }}
        >
          {tool.preview ? (
            <img
              src={tool.preview}
              alt={tool.display_name}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <img
              src="/placeholder.svg"
              alt={tool.display_name}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          )}
        </Box>
      </Box>
      <HoverToolInfo
        anchorEl={anchorEl}
        hoveredTool={hoveredTool}
        handleMouseLeave={handleMouseLeave}
      />
    </>
  );
}
