import React from "react";
import PropTypes from "prop-types";
import { Box, Tooltip } from "@mui/material";

// A count beside a label (e.g. plugin updates in the nav bar and in the
// Installed tab), hidden when zero.
export default function CountBadge({ count, title }) {
  if (!count) return null;
  return (
    <Tooltip title={title}>
      <Box
        component="span"
        sx={{
          ml: 1,
          minWidth: 18,
          height: 18,
          px: 0.5,
          borderRadius: 9,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "primary.main",
          color: "primary.contrastText",
          fontSize: 10,
          letterSpacing: 0,
        }}
      >
        {count}
      </Box>
    </Tooltip>
  );
}

CountBadge.propTypes = {
  count: PropTypes.number,
  title: PropTypes.string,
};
