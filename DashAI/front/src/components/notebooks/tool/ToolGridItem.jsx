import React, { useState } from "react";
import { Box, Typography, Chip, Tooltip } from "@mui/material";
import HoverToolInfo from "./HoverToolInfo";
import api from "../../../api/api";
import { CategoryIcon } from "./CategoryIcon";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

export default function ToolGridItem({ tool, disabled, onClick }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [hoveredTool, setHoveredTool] = useState(null);
  const { t } = useTranslation(["common"]);
  const theme = useTheme();

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
              bgcolor: theme.palette.background.paper,
              color: theme.palette.text.primary,
              display: disabled ? "block" : "none",
              border: `1px solid ${theme.palette.divider}`,
              fontSize: "0.75rem",
              maxWidth: 300,
              "& .MuiTooltip-arrow": {
                color: theme.palette.background.paper,
                "&::before": {
                  border: `1px solid ${theme.palette.divider}`,
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
            bgcolor: disabled
              ? theme.palette.ui.disabled
              : theme.palette.ui.box,
            border: `1px solid ${theme.palette.ui.border}`,
            borderRadius: 1.5,
            overflow: "hidden",
            cursor: disabled ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            opacity: disabled ? 0.5 : 1,
            filter: disabled ? "grayscale(0.6)" : "none",
            "&:hover": {
              bgcolor: disabled
                ? theme.palette.ui.disabled
                : theme.palette.action.hover,
              borderColor: disabled
                ? theme.palette.ui.border
                : tool.metadata.color,
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
              bgcolor: disabled
                ? theme.palette.ui.disabled
                : theme.palette.ui.border,
              borderBottom: `1px solid ${
                disabled ? theme.palette.ui.disabled : theme.palette.ui.border
              }`,
            }}
          >
            <img
              src={`${api.defaults.baseURL}/v1/component/image/${tool.name}/`}
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
          <Box sx={{ p: 3 }}>
            {/* Icon and Badges */}
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 28,
                  height: 28,
                  p: 4,
                  borderRadius: 0.75,
                  bgcolor: disabled
                    ? theme.palette.ui.disabled
                    : theme.palette.ui.border,
                  color: disabled
                    ? theme.palette.text.disabled
                    : theme.palette.text.primary,
                  flexShrink: 0,
                }}
              >
                <CategoryIcon
                  icon={tool.metadata.icon}
                  color={
                    disabled ? theme.palette.text.disabled : tool.metadata.color
                  }
                />
              </Box>
            </Box>

            {/* Title */}
            <Typography
              variant="body2"
              sx={{
                color: disabled
                  ? theme.palette.text.disabled
                  : theme.palette.text.primary,
                fontWeight: 500,
                mb: 1,
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
                color: disabled
                  ? theme.palette.text.disabled
                  : theme.palette.text.primary,
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
