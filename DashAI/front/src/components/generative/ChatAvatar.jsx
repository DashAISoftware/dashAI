import { Avatar as MuiAvatar } from "@mui/material";

export function ChatAvatar({ isUser, alt }) {
  return (
    <MuiAvatar
      src={isUser ? undefined : "/dai_circle.png"}
      alt={alt || (isUser ? "User" : "Model")}
      sx={{
        mr: isUser ? 0 : 1,
        ml: isUser ? 1 : 0,
        width: 32,
        height: 32,
      }}
    />
  );
}
