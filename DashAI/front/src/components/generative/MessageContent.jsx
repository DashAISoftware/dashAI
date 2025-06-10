import { Box, Paper, useTheme } from "@mui/material";
import { TextMessage } from "./TextMessage";
import { ImageMessage } from "./ImageMessage";
import { WaitingAnimationChat } from "./WaitingAnimationChat";

// Helper to create a unique hash from a string
function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
}

export function MessageContent({ messages, isUser, isWaiting }) {
  const theme = useTheme();

  return (
    <Paper
      sx={{
        backgroundColor: "#374151",
        color: "#fff",
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
        messages?.map((message, index) => {
          const type = message["data_type"];
          const key = `${type}-${index}-${simpleHash(JSON.stringify(message))}`;
          return (
            <Box key={key}>
              {type === "str" && <TextMessage message={message.data} />}
              {type === "Image" && <ImageMessage image={message.data} />}
            </Box>
          );
        })
      )}
    </Paper>
  );
}
