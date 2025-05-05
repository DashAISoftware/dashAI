import { Box, Paper, useTheme } from "@mui/material";
import { TextMessage } from "./TextMessage";
import { ImageMessage } from "./ImageMessage";
import { WaitingAnimationChat } from "./WaitingAnimationChat";

export function MessageContent({
  messageType,
  messages,
  cardinality,
  isUser,
  isWaiting,
}) {
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
        messages?.map((message, index) => (
          <Box key={index}>
            {cardinality
              ? messageType[index] === "str"
              : messageType[0] === "str" && <TextMessage message={message} />}
            {cardinality
              ? messageType[index] === "Image"
              : messageType[0] === "Image" && <ImageMessage image={message} />}
          </Box>
        ))
      )}
    </Paper>
  );
}
