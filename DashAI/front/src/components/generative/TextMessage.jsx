import { Box, Typography } from "@mui/material";

export function TextMessage({ messages }) {
  return (
    <Box>
      {messages?.map((message, index) => (
        <Typography key={index} variant="body2" color="text.primary">
          {message}
          {index < messages.length - 1 && <br />}
        </Typography>
      ))}
    </Box>
  );
}
