import React, { useState } from "react";
import { Box, Typography, Tooltip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import HoverModelInfo from "./HoverModelInfo";
import { ModelIcon } from "./ModelIcon";
import { setCustomDragImage } from "../../../utils/dragImage";

export default function ModelListItem({
  model,
  disabled = false,
  draggable = true,
  onClick,
  ...props
}) {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState(null);
  const [hoveredModel, setHoveredModel] = useState(null);

  const handleMouseEnter = (event, model) => {
    if (!disabled) {
      setAnchorEl(event.currentTarget);
      setHoveredModel(model);
    }
  };

  const handleMouseLeave = () => {
    setAnchorEl(null);
    setHoveredModel(null);
  };

  // Get color and icon from metadata or use defaults
  const color =
    model.color || model.metadata?.color || theme.palette.text.secondary;
  const iconName = model.metadata?.icon || "Science";

  return (
    <>
      <Tooltip
        title={disabled && model.tooltip ? model.tooltip : model.description}
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
          key={model.id}
          draggable={!disabled && draggable}
          onDragStart={
            !disabled && draggable
              ? (e) => {
                  e.dataTransfer.setData(
                    "application/x-dashai-model",
                    JSON.stringify(model),
                  );
                  e.dataTransfer.effectAllowed = "copy";
                  setCustomDragImage(e);
                }
              : undefined
          }
          onMouseEnter={(e) => handleMouseEnter(e, model)}
          onMouseLeave={handleMouseLeave}
          onClick={disabled ? null : onClick}
          {...props}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 3,
            p: 3,
            bgcolor: disabled
              ? theme.palette.ui.disabled
              : theme.palette.ui.box,
            border: `1px solid ${theme.palette.ui.border}`,
            borderRadius: 1,
            cursor: disabled ? "not-allowed" : draggable ? "grab" : "pointer",
            transition: "all 0.2s",
            opacity: disabled ? 0.5 : 1,
            filter: disabled ? "grayscale(0.6)" : "none",
            position: "relative",
            "&:hover": {
              bgcolor: disabled
                ? theme.palette.ui.disabled
                : theme.palette.action.hover,
              borderColor: disabled ? theme.palette.ui.border : color,
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
            <ModelIcon
              iconName={iconName}
              color={disabled ? theme.palette.text.disabled : color}
            />
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              variant="body2"
              sx={{
                color: disabled
                  ? theme.palette.text.disabled
                  : theme.palette.text.primary,
                fontWeight: 500,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {model.display_name || model.name}
            </Typography>
          </Box>
        </Box>
      </Tooltip>
      {!disabled && (
        <HoverModelInfo
          anchorEl={anchorEl}
          hoveredModel={hoveredModel}
          handleMouseLeave={handleMouseLeave}
        />
      )}
    </>
  );
}
