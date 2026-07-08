import { Typography, Paper } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import PropTypes from "prop-types";

export default function PresetCard({
  selected = false,
  onClick,
  label,
  description,
  sx: extraSx,
}) {
  const theme = useTheme();

  return (
    <Paper
      variant="outlined"
      onClick={onClick}
      sx={{
        flex: 1,
        cursor: "pointer",
        minHeight: 56,
        px: 3,
        py: 4,
        display: "flex",
        flexDirection: "column",
        gap: 0.5,
        justifyContent: "flex-start",
        border: "1px solid",
        borderColor: selected ? theme.palette.primary.main : theme.palette.ui.border,
        borderRadius: 2,
        backgroundColor: selected ? theme.palette.action.selected : theme.palette.background.paper,
        transition: theme.transitions.create(["background-color", "border-color", "box-shadow"], {
          duration: theme.transitions.duration.short,
        }),
        "&:hover": {
          backgroundColor: selected ? theme.palette.action.selected : theme.palette.action.hover,
          borderColor: theme.palette.primary.main,
        },
        ...extraSx,
      }}
    >
      <Typography variant="subtitle2">
        {label}
      </Typography>
      <Typography variant="caption">
        {description}
      </Typography>
    </Paper>
  );
}

PresetCard.propTypes = {
  selected: PropTypes.bool,
  onClick: PropTypes.func,
  label: PropTypes.string.isRequired,
  description: PropTypes.string,
  sx: PropTypes.object,
};
