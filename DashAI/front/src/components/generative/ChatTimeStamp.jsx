import { Typography } from "@mui/material";

export function ChatTimestamp({ timestamp, isUser }) {
  if (!timestamp) return null;

  return (
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{
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
