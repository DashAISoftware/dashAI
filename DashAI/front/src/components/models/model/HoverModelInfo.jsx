import React from "react";
import { Box, Typography, Popover } from "@mui/material";

export default function HoverModelInfo({
  anchorEl,
  hoveredModel,
  handleMouseLeave,
}) {
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
          bgcolor: "rgb(20, 20, 24)",
          border: "1px solid rgb(63, 63, 70)",
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
            sx={{ color: "rgb(250, 250, 250)", fontWeight: 600, mb: 1 }}
          >
            {hoveredModel.display_name || hoveredModel.name}
          </Typography>

          {/* Description */}
          <Typography
            variant="body2"
            sx={{ color: "rgb(161, 161, 170)", lineHeight: 1.5 }}
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
