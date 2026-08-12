import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";
import PropTypes from "prop-types";
import { getRunStatusColor } from "../../utils/runStatus";

export default function RunStatusDot({ status, size, sx }) {
  const theme = useTheme();
  const statusColorKey = getRunStatusColor(status);
  const statusMain =
    statusColorKey === "default"
      ? theme.palette.text.disabled
      : theme.palette[statusColorKey].main;

  return (
    <Box
      component="span"
      sx={{
        display: "inline-block",
        verticalAlign: "middle",
        width: size,
        height: size,
        borderRadius: "50%",
        bgcolor: statusMain,
        flexShrink: 0,
        ...sx,
      }}
    />
  );
}

RunStatusDot.propTypes = {
  status: PropTypes.number.isRequired,
  size: PropTypes.number,
  sx: PropTypes.object,
};

RunStatusDot.defaultProps = {
  size: 8,
  sx: {},
};
