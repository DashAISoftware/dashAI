import { Box } from "@mui/material";
import PropTypes from "prop-types";

export default function RAGSectionColumn({ children, gap = 4, sx, ...props }) {
  return (
    <Box
      sx={[
        {
          display: "flex",
          flexDirection: "column",
          width: "100%",
          gap,
        },
        sx,
      ]}
      {...props}
    >
      {children}
    </Box>
  );
}

RAGSectionColumn.propTypes = {
  children: PropTypes.node,
  gap: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  sx: PropTypes.oneOfType([PropTypes.array, PropTypes.object, PropTypes.func]),
};
