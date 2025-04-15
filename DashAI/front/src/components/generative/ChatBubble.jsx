import {
  Box,
  Paper,
  Typography,
  Avatar as MuiAvatar,
  styled,
} from "@mui/material";

export function ChatBubble({
  message,
  messageType,
  sender = "",
  timestamp,
  isUser = false,
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        alignItems: "flex-start",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 2,
        width: "100%",
      }}
    >
      {!isUser && (
        <MuiAvatar
          src={"/dai_circle.png"}
          alt={sender || "User"}
          sx={{ mr: 1, width: 32, height: 32 }}
        />
      )}

      <Box sx={{ maxWidth: "80%" }}>
        {!isUser && sender && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ ml: 1, mb: 0.5, display: "block" }}
          >
            {sender}
          </Typography>
        )}

        <Paper
          sx={{
            backgroundColor: "#374151",
            color: "#fff",
            padding: (theme) => theme.spacing(1.5, 2),
            maxWidth: "100%",
            borderRadius: 2,
            borderTopRightRadius: isUser ? 0 : "inherit",
            borderTopLeftRadius: isUser ? "inherit" : 0,
            position: "relative",
          }}
        >
          {messageType === "str" && (
            <Typography variant="body2" color="text.primary">
              {message}
            </Typography>
          )}
          {messageType === "PIL.Image" && (
            <img
              src={`data:image/png;base64,${message}`}
              alt="Image"
              style={{
                maxWidth: "100%",
                maxHeight: "300px",
                objectFit: "contain",
                borderRadius: 8,
                marginTop: 8,
              }}
            />
          )}
        </Paper>

        {timestamp && (
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
        )}
      </Box>

      {isUser && <MuiAvatar alt="User" sx={{ ml: 1, width: 32, height: 32 }} />}
    </Box>
  );
}
