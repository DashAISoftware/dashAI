import { Box } from "@mui/material";
import PropTypes from "prop-types";

export default function SectionCard({ children, sx }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, ...sx }}>
      {children}
    </Box>
  );
}

SectionCard.propTypes = {
  children: PropTypes.node,
  sx: PropTypes.object,
};
