import { Box, Paper, useTheme } from "@mui/material";
import { TextMessage } from "./TextMessage";
import { ImageMessage } from "./ImageMessage";
import { WaitingAnimationChat } from "./WaitingAnimationChat";

export function MessageContent({ messages, isUser, isWaiting }) {
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
      {isWaiting ? (
        <WaitingAnimationChat isActive={isWaiting} />
      ) : (
        messages?.map((message) => {
          const type = message["data_type"];
          return (
            <Box key={message.id}>
              {type === "str" && <TextMessage message={message.data} />}
              {type === "Image" && <ImageMessage image={message.data} />}
            </Box>
          );
        })
      )}
    </Paper>
  );
}
