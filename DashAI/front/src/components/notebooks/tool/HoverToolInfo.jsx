import React from "react";

import { Box, Typography, Popover, Chip } from "@mui/material";
import api from "../../../api/api";
import { useTranslation } from "react-i18next";

export default function HoverToolInfo({
  anchorEl,
  hoveredTool,
  handleMouseLeave,
}) {
  const { t } = useTranslation(["common"]);

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
      {hoveredTool && (
        <Box>
          {/* Large Preview */}
          <Box
            sx={{
              width: "100%",
              height: 160,
              borderRadius: 1.5,
              bgcolor: "rgb(39, 39, 42)",
              border: "1px solid rgb(63, 63, 70)",
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
            sx={{ color: "rgb(250, 250, 250)", fontWeight: 600, mb: 1 }}
          >
            {hoveredTool.display_name}
          </Typography>

          {/* Description */}
          <Typography
            variant="body2"
            sx={{ color: "rgb(161, 161, 170)", lineHeight: 1.5, mb: 1.5 }}
          >
            {hoveredTool.description}
          </Typography>

          {/* Category Badge */}
          <Chip
            label={hoveredTool.metadata.category ?? t("common:other")}
            size="small"
            sx={{
              bgcolor: hoveredTool.metadata.color,
              color: "rgba(255, 255, 255, 1)",
              border: `1px solid rgb(63, 63, 70)`,
              fontWeight: 500,
            }}
          />
        </Box>
      )}
    </Popover>
  );
}
