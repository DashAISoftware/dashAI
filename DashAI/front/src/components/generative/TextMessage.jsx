import { Box, Typography } from "@mui/material";
import Markdown from "react-markdown";

export function TextMessage({ message, isError = false }) {
  return (
    <Box>
      <Typography
        variant="body2"
        component="div"
        color={isError ? "red" : "text.primary"}
      >
        <Markdown>{message}</Markdown>
      </Typography>
    </Box>
  );
}
