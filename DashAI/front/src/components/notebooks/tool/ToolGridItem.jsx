import React, { useState } from "react";
import { Box, Typography, Chip, Tooltip } from "@mui/material";
import HoverToolInfo from "./HoverToolInfo";
import api from "../../../api/api";
import { CategoryIcon } from "./CategoryIcon";
import { useTranslation } from "react-i18next";

export default function ToolGridItem({ tool, disabled, onClick }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [hoveredTool, setHoveredTool] = useState(null);
  const { t } = useTranslation(["common"]);

  const handleMouseEnter = (event, tool) => {
    if (!disabled) {
      setAnchorEl(event.currentTarget);
      setHoveredTool(tool);
    }
  };

  const handleMouseLeave = () => {
    setAnchorEl(null);
    setHoveredTool(null);
  };

  return (
    <>
      <Tooltip
        title={disabled && tool.tooltip ? tool.tooltip : tool.description}
        arrow
        placement="top"
        slotProps={{
          tooltip: {
            sx: {
              bgcolor: "rgb(33, 33, 33)",
              display: disabled ? "block" : "none",
              color: "rgb(255, 255, 255)",
              border: "1px solid rgb(63, 63, 70)",
              fontSize: "0.75rem",
              maxWidth: 300,
              "& .MuiTooltip-arrow": {
                color: "rgb(33, 33, 33)",
                "&::before": {
                  border: "1px solid rgb(63, 63, 70)",
                },
              },
            },
          },
        }}
      >
        <Box
          key={tool.id}
          onMouseEnter={(e) => handleMouseEnter(e, tool)}
          onMouseLeave={handleMouseLeave}
          onClick={disabled ? null : onClick}
          sx={{
            position: "relative",
            bgcolor: disabled ? "rgb(32, 32, 32)" : "rgb(44, 44, 44)",
            border: "1px solid rgb(39, 39, 42)",
            borderRadius: 1.5,
            overflow: "hidden",
            cursor: disabled ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            opacity: disabled ? 0.5 : 1,
            filter: disabled ? "grayscale(0.6)" : "none",
            "&:hover": {
              bgcolor: disabled ? "rgb(32, 32, 32)" : "rgb(60, 60, 60)",
              borderColor: disabled ? "rgb(39, 39, 42)" : tool.metadata.color,
              transform: disabled ? "none" : "translateY(-4px)",
              boxShadow: disabled ? "none" : `0 8px 16px rgba(0, 0, 0, 0.2)`,
            },
            "&::after": disabled
              ? {
                  content: '""',
                  position: "absolute",
                  inset: 0,
                  borderRadius: 1.5,
                  pointerEvents: "none",
                  background:
                    "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0, 0, 0, 0.1) 10px, rgba(0, 0, 0, 0.1) 20px)",
                  zIndex: 2,
                }
              : {},
          }}
        >
          {/* Preview Image */}
          <Box
            sx={{
              width: "100%",
              height: 100,
              bgcolor: disabled ? "rgb(30, 30, 30)" : "rgb(39, 39, 42)",
              borderBottom: "1px solid rgb(39, 39, 42)",
            }}
          >
            <img
              src={`${api.defaults.baseURL}/v1/component/image/${tool.name}`}
              alt={tool.display_name}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                opacity: disabled ? 0.4 : 1,
              }}
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
                  bgcolor: disabled ? "rgb(50, 50, 50)" : "rgb(63, 63, 70)",
                  color: disabled ? "rgb(150, 150, 150)" : "rgb(250, 250, 250)",
                  flexShrink: 0,
                }}
              >
                <CategoryIcon
                  name={tool.type}
                  category={tool.metadata.category}
                  color={disabled ? "rgb(100, 100, 100)" : tool.metadata.color}
                />
              </Box>
            </Box>

            {/* Title */}
            <Typography
              variant="body2"
              sx={{
                color: disabled ? "rgb(150, 150, 150)" : "rgb(250, 250, 250)",
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
              {tool.display_name || tool.name}
            </Typography>

            {/* Category */}
            <Typography
              variant="caption"
              sx={{
                color: disabled ? "rgb(90, 90, 90)" : "rgb(113, 113, 122)",
              }}
            >
              {tool.metadata.category ?? t("common:other")}
            </Typography>
          </Box>
        </Box>
      </Tooltip>
      {!disabled && (
        <HoverToolInfo
          anchorEl={anchorEl}
          hoveredTool={hoveredTool}
          handleMouseLeave={handleMouseLeave}
        />
      )}
    </>
  );
}
