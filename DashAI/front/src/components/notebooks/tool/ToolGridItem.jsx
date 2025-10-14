import React, { useState } from "react";

import { Box, Typography, Chip } from "@mui/material";
import HoverToolInfo from "./HoverToolInfo";
import api from "../../../api/api";
import { CategoryIcon } from "./CategoryIcon";

export default function ToolGridItem({ tool, disabled, onClick }) {
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
        sx={{
          position: "relative",
          bgcolor: "rgb(44, 44, 44)",
          border: "1px solid rgb(39, 39, 42)",
          borderRadius: 1.5,
          overflow: "hidden",
          cursor: "pointer",
          transition: "all 0.2s",
          "&:hover": {
            bgcolor: disabled ? "rgb(44, 44, 44)" : "rgb(60, 60, 60)",
            borderColor: disabled ? "rgb(39, 39, 42)" : tool.metadata.color,
            transform: disabled ? "none" : "translateY(-4px)",
            boxShadow: `0 8px 16px ${
              disabled ? "transparent" : "rgba(0, 0, 0, 0.2)"
            }`,
          },
        }}
      >
        {/* Preview Image */}
        <Box
          sx={{
            width: "100%",
            height: 100,
            bgcolor: "rgb(39, 39, 42)",
            borderBottom: "1px solid rgb(39, 39, 42)",
          }}
        >
          <img
            src={`${api.defaults.baseURL}/v1/component/image/${tool.name}`}
            alt={tool.display_name}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </Box>

        {/* Content */}
        <Box sx={{ p: 1.5 }}>
          {/* Icon and Badges */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 28,
                height: 28,
                borderRadius: 0.75,
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
          </Box>

          {/* Title */}
          <Typography
            variant="body2"
            sx={{
              color: "rgb(250, 250, 250)",
              fontWeight: 500,
              mb: 0.5,
              overflow: "hidden",
              textOverflow: "ellipsis",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              lineHeight: 1.3,
              minHeight: "2.6em",
            }}
          >
            {tool.display_name}
          </Typography>

          {/* Category */}
          <Typography variant="caption" sx={{ color: "rgb(113, 113, 122)" }}>
            {tool.metadata.category ?? "Other"}
          </Typography>
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
