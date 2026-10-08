import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Discreet outlined button used for secondary actions
 * ("Nuevo proyecto", "Ver permisos", ...).
 */
export default function ActionButton({ icon: Icon, onClick, children, sx }) {
  const theme = useTheme();

  return (
    <Box
      component="button"
      type="button"
      onClick={onClick}
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 1,
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 1,
        background: "transparent",
        color: theme.palette.text.secondary,
        px: 2,
        py: 1,
        cursor: "pointer",

        "&:hover": {
          background: theme.palette.ui.hover,
          color: theme.palette.text.primary,
        },
        ...sx,
      }}
    >
      {Icon && <Icon sx={{ fontSize: 18 }} />}
      <Typography component="span" variant="body2" sx={{ color: "inherit" }}>
        {children}
      </Typography>
    </Box>
  );
}

ActionButton.propTypes = {
  icon: PropTypes.elementType,
  onClick: PropTypes.func,
  children: PropTypes.node.isRequired,
  sx: PropTypes.object,
};
