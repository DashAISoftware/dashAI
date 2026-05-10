import { Box } from "@mui/material";
import { ChatAvatar } from "./ChatAvatar";
import { ChatTimestamp } from "./ChatTimeStamp";
import { MessageContent } from "./MessageContent";

export function ChatBubble({
  messages,
  sender = "",
  timestamp = null,
  isUser = false,
  isWaiting = false,
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        alignItems: "flex-start",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 4,
        width: "100%",
      }}
    >
      {!isUser && <ChatAvatar isUser={isUser} alt={sender || undefined} />}

      <Box sx={{ maxWidth: "80%" }}>
        {!isUser && sender && (
          <Box
            component="span"
            sx={{
              ml: 2,
              mb: 1,
              display: "block",
              fontSize: "0.75rem",
              color: "text.secondary",
            }}
          >
            {sender}
          </Box>
        )}

        <MessageContent
          messages={messages}
          isUser={isUser}
          isWaiting={isWaiting}
        />

        <ChatTimestamp timestamp={timestamp} isUser={isUser} />
      </Box>

      {isUser && <ChatAvatar isUser={isUser} />}
    </Box>
  );
}
