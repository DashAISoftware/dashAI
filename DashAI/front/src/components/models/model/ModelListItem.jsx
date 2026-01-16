import React, { useState } from "react";
import { Box, Typography, Tooltip } from "@mui/material";
import HoverModelInfo from "./HoverModelInfo";
import { ModelIcon } from "./ModelIcon";

export default function ModelListItem({
  model,
  disabled = false,
  onClick,
  ...props
}) {
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
  const color = model.color || model.metadata?.color || "#795548";
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
              bgcolor: "rgb(33, 33, 33)",
              color: "rgb(255, 255, 255)",
              display: disabled ? "block" : "none",
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
          key={model.id}
          onMouseEnter={(e) => handleMouseEnter(e, model)}
          onMouseLeave={handleMouseLeave}
          onClick={disabled ? null : onClick}
          {...props}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            p: 1.5,
            bgcolor: disabled ? "rgb(32, 32, 32)" : "rgb(44, 44, 44)",
            border: "1px solid rgb(39, 39, 42)",
            borderRadius: 1,
            cursor: disabled ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            opacity: disabled ? 0.5 : 1,
            filter: disabled ? "grayscale(0.6)" : "none",
            position: "relative",
            "&:hover": {
              bgcolor: disabled ? "rgb(32, 32, 32)" : "rgb(60, 60, 60)",
              borderColor: disabled ? "rgb(39, 39, 42)" : color,
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
              bgcolor: disabled ? "rgb(50, 50, 50)" : "rgb(63, 63, 70)",
              color: disabled ? "rgb(150, 150, 150)" : "rgb(250, 250, 250)",
              flexShrink: 0,
            }}
          >
            <ModelIcon
              iconName={iconName}
              color={disabled ? "rgb(100, 100, 100)" : color}
            />
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              variant="body2"
              sx={{
                color: disabled ? "rgb(150, 150, 150)" : "rgb(250, 250, 250)",
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
