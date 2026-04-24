import { Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export function ChatTimestamp({ timestamp, isUser }) {
  const theme = useTheme();

  if (!timestamp) return null;

  return (
    <Typography
      variant="caption"
      sx={{
        color: theme.palette.text.secondary,
        display: "block",
        mt: 0.5,
        textAlign: isUser ? "right" : "left",
        px: 1,
      }}
    >
      {timestamp}
    </Typography>
  );
}
