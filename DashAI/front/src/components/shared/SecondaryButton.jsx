import { Button } from "@mui/material";
import { useTheme } from "@mui/material/styles";

/**
 * A neutral secondary button that does not use the primary or secondary palette color.
 * Use it for auxiliary actions like "Browse", "Cancel", or "Clear".
 */
export default function SecondaryButton({ sx, ...props }) {
  const theme = useTheme();

  return (
    <Button
      variant="contained"
      sx={{
        backgroundColor: theme.palette.ui.panelLight,
        color: theme.palette.text.primary,
        border: `1px solid ${theme.palette.ui.borderDark}`,
        boxShadow: "none",
        "&:hover": {
          backgroundColor: theme.palette.ui.panelMedium,
          boxShadow: "none",
        },
        "&:active": {
          boxShadow: "none",
        },
        "&.Mui-disabled": {
          backgroundColor: theme.palette.ui.disabled,
          color: theme.palette.text.disabled,
          borderColor: theme.palette.ui.border,
        },
        ...sx,
      }}
      {...props}
    />
  );
}
