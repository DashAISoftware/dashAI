import React from "react";
import { Box, Typography, Popover } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function HoverModelInfo({
  anchorEl,
  hoveredModel,
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
      {hoveredModel && (
        <Box>
          {/* Title */}
          <Typography
            variant="subtitle2"
            sx={{ color: theme.palette.text.primary, fontWeight: 600, mb: 1 }}
          >
            {hoveredModel.display_name || hoveredModel.name}
          </Typography>

          {/* Description */}
          <Typography
            variant="body2"
            sx={{ color: theme.palette.text.secondary, lineHeight: 1.5 }}
          >
            {hoveredModel.description ||
              hoveredModel.metadata?.description ||
              "No description available"}
          </Typography>
        </Box>
      )}
    </Popover>
  );
}
