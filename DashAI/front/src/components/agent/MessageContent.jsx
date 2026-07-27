import { Paper, Typography, useTheme } from "@mui/material";
import { WaitingAnimationChat } from "../generative/WaitingAnimationChat";

export default function MessageContent({ text, isUser, isWaiting }) {
  const theme = useTheme();

  return (
    <Paper
      sx={{
        backgroundColor: theme.palette.ui.box,
        color: "text.primary",
        padding: theme.spacing(1.5, 2),
        maxWidth: "100%",
        borderRadius: 2,
        borderTopRightRadius: isUser ? 0 : "inherit",
        borderTopLeftRadius: isUser ? "inherit" : 0,
        position: "relative",
      }}
    >
      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {isWaiting ? <WaitingAnimationChat isActive={isWaiting}/> : text || ""}
      </Typography>
    </Paper>
  );
}
