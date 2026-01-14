import React, { useState } from "react";
import { Box, Typography, Chip, Tooltip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import HoverToolInfo from "./HoverToolInfo";
import api from "../../../api/api";
import { CategoryIcon } from "./CategoryIcon";

export default function ToolListItem({
  tool,
  disabled = false,
  onClick,
  ...props
}) {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState(null);
  const [hoveredTool, setHoveredTool] = useState(null);

  const handleMouseEnter = (event, tool) => {
    if (!disabled) {
      setAnchorEl(event.currentTarget);
      setHoveredTool(tool);
    }
  };

  const getTourAttribute = () => {
    if (tool.name === "HistogramPlotExplorer") {
      return "histogram-explorer";
    }
    if (tool.name === "LabelEncoder") {
      return "label-encoder-converter";
    }
    if (tool.name === "NanRemover") {
      return "nan-remover-converter";
    }
    return undefined;
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
          data-tour={getTourAttribute()}
          {...props}
          onMouseEnter={(e) => handleMouseEnter(e, tool)}
          onMouseLeave={handleMouseLeave}
          onClick={disabled ? null : onClick}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            p: 1.5,
            bgcolor: disabled
              ? theme.palette.ui.disabled
              : theme.palette.ui.box,
            border: `1px solid ${theme.palette.ui.border}`,
            borderRadius: 1,
            cursor: disabled ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            opacity: disabled ? 0.5 : 1,
            filter: disabled ? "grayscale(0.6)" : "none",
            position: "relative",
            "&:hover": {
              bgcolor: disabled
                ? theme.palette.ui.disabled
                : theme.palette.action.hover,
              borderColor: disabled
                ? theme.palette.ui.border
                : tool.metadata.color,
              transform: disabled ? "none" : "translateX(4px)",
            },
            "&::after": disabled
              ? {
                  content: '""',
                  position: "absolute",
                  inset: 0,
                  borderRadius: 1,
                  pointerEvents: "none",
                  background:
                    "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0, 0, 0, 0.1) 10px, rgba(0, 0, 0, 0.1) 20px)",
                }
              : {},
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
              name={tool.type}
              category={tool.metadata.category}
              color={
                disabled ? theme.palette.text.disabled : tool.metadata.color
              }
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
                  color: disabled
                    ? theme.palette.text.disabled
                    : theme.palette.text.primary,
                  fontWeight: 500,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  width: 0,
                  flexGrow: 1,
                  whiteSpace: "nowrap",
                }}
              >
                {tool.display_name || tool.name}
              </Typography>
            </Box>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                mb: 0.5,
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  color: disabled
                    ? theme.palette.text.disabled
                    : theme.palette.text.secondary,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  width: 0,
                  flexGrow: 1,
                  whiteSpace: "nowrap",
                }}
              >
                {tool.metadata.category ?? "Other"}
              </Typography>
            </Box>
          </Box>

          {/* Preview Thumbnail */}
          <Box
            sx={{
              width: 60,
              height: 40,
              borderRadius: 0.75,
              bgcolor: disabled
                ? theme.palette.ui.disabled
                : theme.palette.ui.border,
              border: `1px solid ${
                disabled ? theme.palette.ui.disabled : theme.palette.ui.border
              }`,
              display: { xs: "none", lg: "none", xl: "block" },
              overflow: "hidden",
              flexShrink: 0,
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
