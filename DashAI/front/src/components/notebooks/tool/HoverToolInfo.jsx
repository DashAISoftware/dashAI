import React from "react";

import { Box, Typography, Popover, Chip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import api from "../../../api/api";

export default function HoverToolInfo({
  anchorEl,
  hoveredTool,
  handleMouseLeave,
}) {
  const theme = useTheme();

  return (
    <Popover
      open={Boolean(anchorEl)}
      anchorEl={anchorEl}
      onClose={handleMouseLeave}
      anchorOrigin={{
        vertical: "center",
        horizontal: "left",
      }}
      transformOrigin={{
        vertical: "center",
        horizontal: "right",
      }}
      disableRestoreFocus
      sx={{
        pointerEvents: "none",
        "& .MuiPopover-paper": {
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 2,
          p: 2,
          maxWidth: 320,
          ml: -1,
        },
      }}
    >
      {hoveredTool && (
        <Box>
          {/* Large Preview */}
          <Box
            sx={{
              width: "100%",
              height: 160,
              borderRadius: 1.5,
              bgcolor: "ui.border",
              border: `1px solid ${theme.palette.divider}`,
              overflow: "hidden",
              mb: 2,
            }}
          >
            <img
              src={`${api.defaults.baseURL}/v1/component/image/${hoveredTool.name}`}
              alt={hoveredTool.display_name}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </Box>

          {/* Title */}
          <Typography
            variant="subtitle2"
            sx={{ color: "text.primary", fontWeight: 600, mb: 1 }}
          >
            {hoveredTool.display_name}
          </Typography>

          {/* Description */}
          <Typography
            variant="body2"
            sx={{ color: "text.secondary", lineHeight: 1.5, mb: 1.5 }}
          >
            {hoveredTool.description}
          </Typography>

          {/* Category Badge */}
          <Chip
            label={hoveredTool.metadata.category ?? "Other"}
            size="small"
            sx={{
              bgcolor: hoveredTool.metadata.color,
              color: "rgba(255, 255, 255, 1)",
              border: `1px solid ${theme.palette.divider}`,
              fontWeight: 500,
            }}
          />
        </Box>
      )}
    </Popover>
  );
}
