import React from "react";
import { Box, Typography, useTheme } from "@mui/material";

const IssueCard = ({ title, count, items, severity = "info" }) => {
  const theme = useTheme();
  const palette = theme.palette[severity] || theme.palette.info;

  return (
    <Box
      sx={{
        p: 4,
        border: `1px solid ${palette.light}`,
        borderRadius: 2,
        bgcolor: theme.palette.ui.panelDark,
        color: palette.main,
        display: "flex",
        flexDirection: "column",
        gap: 1,
      }}
    >
      {/* Header */}
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mb={1}
      >
        <Typography variant="body2" fontWeight={500}>
          {title}
        </Typography>
        <Typography variant="caption" fontWeight="bold">
          {count}
        </Typography>
      </Box>

      {/* Items */}
      {items.length > 0 && (
        <Typography variant="caption">
          {items.slice(0, 3).join(", ")}
          {items.length > 3 && "..."}
        </Typography>
      )}
    </Box>
  );
};

export default IssueCard;
