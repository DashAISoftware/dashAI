import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import CloseIcon from "@mui/icons-material/Close";

import SectionLabel from "./SectionLabel";

/**
 * Right-side panel showing the details of the selected item.
 * When `title` is empty it renders `emptyMessage` instead.
 */
export default function DetailPanel({
  title,
  subtitle,
  onClose,
  emptyMessage,
  children,
}) {
  const theme = useTheme();

  if (!title) {
    return (
      <Box
        sx={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          px: 4,
          textAlign: "center",
        }}
      >
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.disabled, lineHeight: 1.6 }}
        >
          {emptyMessage}
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 4,
          py: 3,
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: "flex",
          alignItems: "flex-start",
          gap: 2,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="h6"
            sx={{ color: theme.palette.text.primary, mb: 0.5 }}
          >
            {title}
          </Typography>

          {subtitle && (
            <Typography
              variant="caption"
              sx={{
                color: theme.palette.text.disabled,
                fontFamily: '"Geist Mono", monospace',
              }}
            >
              {subtitle}
            </Typography>
          )}
        </Box>

        {onClose && (
          <Box
            component="button"
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            sx={{
              border: "none",
              background: "transparent",
              color: theme.palette.text.disabled,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 0.5,

              "&:hover": {
                color: theme.palette.text.primary,
                background: theme.palette.ui.hover,
              },
            }}
          >
            <CloseIcon sx={{ fontSize: 18 }} />
          </Box>
        )}
      </Box>

      {/* Body */}
      <Box sx={{ flex: 1, overflow: "auto", p: 4 }}>{children}</Box>
    </Box>
  );
}

DetailPanel.propTypes = {
  title: PropTypes.node,
  subtitle: PropTypes.node,
  onClose: PropTypes.func,
  emptyMessage: PropTypes.node,
  children: PropTypes.node,
};

/**
 * Titled block inside a DetailPanel. Consecutive sections are separated
 * by a divider.
 */
export function DetailSection({ label, children }) {
  const theme = useTheme();

  return (
    <Box
      sx={{
        py: 4,
        borderBottom: `1px solid ${theme.palette.divider}`,
        "&:first-of-type": { pt: 0 },
        "&:last-of-type": { pb: 0, borderBottom: "none" },
      }}
    >
      <SectionLabel sx={{ letterSpacing: "0.1em" }}>{label}</SectionLabel>
      <Box sx={{ mt: 3 }}>{children}</Box>
    </Box>
  );
}

DetailSection.propTypes = {
  label: PropTypes.node.isRequired,
  children: PropTypes.node,
};

/**
 * Label / value pair inside a DetailSection.
 */
export function DetailField({ label, children }) {
  const theme = useTheme();

  return (
    <Box sx={{ "& + &": { mt: 2 } }}>
      <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
        {label}
      </Typography>
      <Typography
        variant="body2"
        component="div"
        sx={{ color: theme.palette.text.primary, mt: 0.5 }}
      >
        {children}
      </Typography>
    </Box>
  );
}

DetailField.propTypes = {
  label: PropTypes.node.isRequired,
  children: PropTypes.node,
};
