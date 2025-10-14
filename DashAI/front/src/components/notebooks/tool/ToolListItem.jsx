import React, { useState } from "react";

import { Box, Typography, Chip } from "@mui/material";
import HoverToolInfo from "./HoverToolInfo";
import api from "../../../api/api";
import { CategoryIcon } from "./CategoryIcon";

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
          bgcolor: "rgb(44, 44, 44)",
          border: "1px solid rgb(39, 39, 42)",
          borderRadius: 1,
          cursor: disabled ? "not-allowed" : "pointer",
          transition: "all 0.2s",
          "&:hover": {
            bgcolor: disabled ? "rgb(44, 44, 44)" : "rgb(60, 60, 60)",
            borderColor: disabled ? "rgb(39, 39, 42)" : tool.metadata.color,
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
          <CategoryIcon
            category={tool.metadata.category}
            color={tool.metadata.color}
          />
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              mb: 0.5,
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: "rgb(250, 250, 250)",
                fontWeight: 500,
                overflow: "hidden",
                textOverflow: "ellipsis",
                width: 0,
                flexGrow: 1,
                whiteSpace: "nowrap",
              }}
            >
              {tool.display_name}
            </Typography>
          </Box>
          <Typography variant="caption" sx={{ color: "rgb(113, 113, 122)" }}>
            {tool.metadata.category ?? "Other"}
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
          <img
            src={`${api.defaults.baseURL}/v1/component/image/${tool.name}`}
            alt={tool.display_name}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
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
