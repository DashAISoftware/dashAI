import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function DescriptionPanel() {
  const theme = useTheme();
  return (
    <Box
      sx={{
        p: 2,
        bgcolor: theme.palette.ui.panelDark,
        borderTop: `1px solid ${theme.palette.ui.borderLight}`,
        minHeight: 80,
        maxHeight: 80,
        display: "flex",
        alignItems: "center",
        flexShrink: 0,
      }}
    >
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", fontStyle: "italic" }}
      >
        Hover over a tool to see its description
      </Typography>
    </Box>
  );
}
