import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function NoteBox({ message, className = "" }) {
  const theme = useTheme();
  return (
    <Box
      className={className}
      sx={{
        mt: 2,
        p: 2,
        bgcolor: theme.palette.background.box,
        borderRadius: 1,
        border: `1px solid ${theme.palette.ui.divider}`,
        mb: 2,
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{ color: theme.palette.primary.main, mb: 1 }}
      >
        Note:
      </Typography>
      <Typography variant="body2">{message}</Typography>
    </Box>
  );
}
