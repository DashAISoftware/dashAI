import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "./textMessage/CodeBlock";
import { InlineCode } from "./textMessage/InlineCode";

const remarkPlugins = [remarkGfm];

const markdownComponents = {
  table: ({ children }) => (
    <TableContainer component={Paper} variant="outlined" sx={{ my: 1.5 }}>
      <Table size="small">{children}</Table>
    </TableContainer>
  ),
  thead: ({ children }) => <TableHead>{children}</TableHead>,
  tbody: ({ children }) => <TableBody>{children}</TableBody>,
  tr: ({ children }) => <TableRow>{children}</TableRow>,
  th: ({ children, style }) => (
    <TableCell sx={{ fontWeight: 600 }} align={style?.textAlign}>
      {children}
    </TableCell>
  ),
  td: ({ children, style }) => (
    <TableCell align={style?.textAlign}>{children}</TableCell>
  ),
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
        variant="body1"
        component="div"
        color={isError ? "red" : "text.primary"}
      >
        <Markdown remarkPlugins={remarkPlugins} components={markdownComponents}>
          {message}
        </Markdown>
      </Typography>
    </Box>
  );
}
