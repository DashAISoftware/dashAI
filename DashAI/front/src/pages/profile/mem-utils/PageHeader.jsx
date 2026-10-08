import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Title bar shown at the top of the main content of a profile view.
 */
export default function PageHeader({ title, subtitle }) {
  const theme = useTheme();

  return (
    <Box
      sx={{
        px: 6,
        py: 4,
        borderBottom: `1px solid ${theme.palette.divider}`,
        background: theme.palette.background.default,
      }}
    >
      <Typography variant="h3" sx={{ color: theme.palette.text.primary }}>
        {title}
      </Typography>

      {subtitle && (
        <Typography
          variant="body2"
          sx={{
            color: theme.palette.text.disabled,
            fontWeight: 300,
            lineHeight: 1.65,
            mt: 1,
          }}
        >
          {subtitle}
        </Typography>
      )}
    </Box>
  );
}

PageHeader.propTypes = {
  title: PropTypes.node.isRequired,
  subtitle: PropTypes.node,
};
