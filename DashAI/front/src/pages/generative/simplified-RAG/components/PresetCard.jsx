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
        py: 1.5,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 0.5,
        justifyContent: "center",
        textTransform: "none",
        border: "1px solid",
        borderColor: selected ? theme.palette.accent.amberBorder : "divider",
        borderRadius: selected ? "2px" : 1,
        backgroundColor: selected ? theme.palette.accent.amberDim : "transparent",
        color: selected ? theme.palette.primary.main : "inherit",
        "&:hover": selected
          ? {
              backgroundColor: theme.palette.primary.main,
              color: theme.palette.primary.contrastText,
              "& .MuiTypography-root": {
                color: theme.palette.primary.contrastText,
              },
            }
          : {},
        ...extraSx,
      }}
    >
      <Typography variant="subtitle2" sx={{ textAlign: "center" }}>
        {label}
      </Typography>
      <Typography variant="caption" sx={{ textAlign: "center" }}>
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
