import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Heading of a content block: title, optional subtitle (e.g. a counter)
 * and an optional action aligned to the right.
 */
export default function ContentHeader({ title, subtitle, action }) {
  const theme = useTheme();

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 2,
        mb: 4,
      }}
    >
      <Box>
        <Typography variant="h5" sx={{ color: theme.palette.text.primary }}>
          {title}
        </Typography>

        {subtitle && (
          <Typography
            variant="body2"
            sx={{ color: theme.palette.text.disabled, mt: 0.5 }}
          >
            {subtitle}
          </Typography>
        )}
      </Box>

      {action}
    </Box>
  );
}

ContentHeader.propTypes = {
  title: PropTypes.node.isRequired,
  subtitle: PropTypes.node,
  action: PropTypes.node,
};
