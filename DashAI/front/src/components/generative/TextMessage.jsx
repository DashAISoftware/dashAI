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

// The text of a hast node and its descendants.
const textOf = (node) =>
  node.type === "text"
    ? node.value
    : (node.children || []).map(textOf).join("");

// The language of a code element, from its `language-*` class, if any.
const languageOf = (code) =>
  (code.properties?.className || [])
    .map(String)
    .find((name) => name.startsWith("language-"))
    ?.slice("language-".length);

// A block without a language whose text is JSON is shown as JSON. Only text
// that starts like JSON is parsed, so prose and code stay cheap to render.
const guessLanguage = (text) => {
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
    return null;
  }
  try {
    JSON.parse(trimmed);
    return "json";
  } catch {
    return null;
  }
};

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
  // A fenced or indented block is a <code> inside a <pre>; inline code has no
  // <pre>. react-markdown v9 no longer says which is which, and a block may
  // have no language, so the block is decided here, from the <pre> (#964).
  pre({ node, children }) {
    const code = node?.children?.find((child) => child.tagName === "code");
    if (!code) {
      return <pre>{children}</pre>;
    }
    const text = textOf(code);
    const language = languageOf(code) || guessLanguage(text) || "text";
    return <CodeBlock language={language}>{text}</CodeBlock>;
  },
  code({ node, className, children, ...props }) {
    return <InlineCode {...props}>{children}</InlineCode>;
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
