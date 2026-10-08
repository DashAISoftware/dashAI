import React from "react";
import PropTypes from "prop-types";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Small uppercase monospace label used to title sidebar groups and
 * detail panel sections.
 */
export default function SectionLabel({ children, sx }) {
  const theme = useTheme();

  return (
    <Typography
      variant="caption"
      sx={{
        display: "block",
        color: theme.palette.text.disabled,
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        fontFamily: '"Geist Mono", monospace',
        ...sx,
      }}
    >
      {children}
    </Typography>
  );
}

SectionLabel.propTypes = {
  children: PropTypes.node.isRequired,
  sx: PropTypes.object,
};
