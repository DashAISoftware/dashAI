import { Box, Typography } from "@mui/material";
import Markdown from "react-markdown";
import { CodeBlock } from "./textMessage/CodeBlock";
import { InlineCode } from "./textMessage/InlineCode";

const markdownComponents = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    if (match) {
      return <CodeBlock language={match[1]}>{children}</CodeBlock>;
    }
    return <InlineCode {...props}>{children}</InlineCode>;
  },
  pre({ children }) {
    return <>{children}</>;
  },
};

export function TextMessage({ message, isError = false }) {
  return (
    <Box>
      <Typography
        variant="body2"
        component="div"
        color={isError ? "red" : "text.primary"}
      >
        <Markdown components={markdownComponents}>{message}</Markdown>
      </Typography>
    </Box>
  );
}
