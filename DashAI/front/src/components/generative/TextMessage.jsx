import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
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
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTranslation } from "react-i18next";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "./textMessage/CodeBlock";
import { InlineCode } from "./textMessage/InlineCode";

// A complete reasoning block: an opening <think ...> or <thinking ...> tag
// paired with its own closing tag. Only complete pairs are recognised, so a
// tag that is still streaming stays ordinary text and never hides the reply.
// Groups: 1 opening tag, 2 tag name, 3 body, 4 closing tag.
const REASONING_BLOCK = /(<(think|thinking)\b[^<>]*>)([\s\S]*?)(<\/\2\s*>)/gi;

// The fence that opens a fenced code block on `line`, if any: the character
// that must close it and its length, since a closing fence is at least as long.
const openingFence = (line) => {
  let normalized = line;
  let quoteDepth = 0;
  let quotePrefix = /^ {0,3}> ?/.exec(normalized);
  while (quotePrefix) {
    normalized = normalized.slice(quotePrefix[0].length);
    quoteDepth += 1;
    quotePrefix = /^ {0,3}> ?/.exec(normalized);
  }
  const listPrefix = /^ {0,3}(?:[-+*]|\d+[.)]) +/.exec(normalized);
  if (listPrefix) {
    normalized = `  ${normalized.slice(listPrefix[0].length)}`;
  }
  const match = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(normalized);
  // A backtick fence's info string cannot hold backticks (CommonMark).
  if (!match || (match[1][0] === "`" && match[2].includes("`"))) {
    return null;
  }
  return { char: match[1][0], length: match[1].length, quoteDepth };
};

// Whether `line` closes `fence`: the same character, at least as long, and
// followed by nothing but whitespace.
const closingFence = (line, fence) => {
  let normalized = line;
  for (let depth = 0; depth < fence.quoteDepth; depth += 1) {
    const quotePrefix = /^ {0,3}> ?/.exec(normalized);
    if (!quotePrefix) {
      return false;
    }
    normalized = normalized.slice(quotePrefix[0].length);
  }
  const match = /^ {0,3}(`{3,}|~{3,})\s*$/.exec(normalized);
  return (
    match !== null &&
    match[1][0] === fence.char &&
    match[1].length >= fence.length
  );
};

// The [start, end) ranges of the fenced code blocks of a Markdown source. An
// unclosed fence runs to the end of the message, as Markdown reads it.
const fencedRanges = (source) => {
  const ranges = [];
  let offset = 0;
  let fence = null;
  for (const line of source.split("\n")) {
    const start = offset;
    offset += line.length + 1;
    if (fence === null) {
      const opened = openingFence(line);
      if (opened !== null) {
        fence = { ...opened, start };
      }
    } else if (closingFence(line, fence)) {
      ranges.push([fence.start, start + line.length]);
      fence = null;
    }
  }
  if (fence !== null) {
    ranges.push([fence.start, source.length]);
  }
  return ranges;
};

// The end of the first run of exactly `length` backticks in [from, to), or null
// when no matching delimiter exists.
const closingBackticks = (source, from, to, length) => {
  const signposts = /`+/g;
  signposts.lastIndex = from;
  let match = signposts.exec(source);
  while (match !== null && match.index < to) {
    if (match[0].length === length) {
      return match.index + match[0].length;
    }
    match = signposts.exec(source);
  }
  return null;
};

// The [start, end) ranges of the inline `code spans` of a region that holds no
// fenced block, so an unmatched backtick stays literal text.
const inlineCodeRanges = (source, from, to) => {
  const ranges = [];
  const runs = /`+/g;
  let cursor = from;
  while (cursor < to) {
    runs.lastIndex = cursor;
    const open = runs.exec(source);
    if (open === null || open.index >= to) {
      break;
    }
    const contentStart = open.index + open[0].length;
    const end = closingBackticks(source, contentStart, to, open[0].length);
    if (end === null) {
      cursor = contentStart;
      continue;
    }
    ranges.push([open.index, end]);
    cursor = end;
  }
  return ranges;
};

// The [start, end) ranges of a Markdown source that reasoning tags must not be
// read from: fenced blocks and inline code spans, in document order.
const codeRanges = (source) => {
  const ranges = [];
  let cursor = 0;
  for (const [start, end] of fencedRanges(source)) {
    ranges.push(...inlineCodeRanges(source, cursor, start), [start, end]);
    cursor = end;
  }
  ranges.push(...inlineCodeRanges(source, cursor, source.length));
  return ranges;
};

// Replaces every protected character with a placeholder of the same length, so
// tag positions still map to the original message while code stops reading as
// a tag.
const maskRanges = (source, ranges) => {
  const characters = source.split("");
  for (const [start, end] of ranges) {
    characters.fill("\u0000", start, end);
  }
  return characters.join("");
};

// Splits a message into ordered segments: `reasoning` text from complete
// <think ...>...</think ...> pairs and the `answer` Markdown between them.
// Nothing is reordered or joined, an incomplete tag stays ordinary text, and
// non-string data is returned untouched as a single answer.
const splitReasoning = (message) => {
  if (typeof message !== "string") {
    return [{ type: "answer", text: message }];
  }

  const masked = maskRanges(message, codeRanges(message));
  const segments = [];
  let cursor = 0;

  for (const match of masked.matchAll(REASONING_BLOCK)) {
    const [whole, opening, , , closing] = match;
    const start = match.index;
    const end = start + whole.length;

    const answer = message.slice(cursor, start);
    if (answer !== "") {
      segments.push({ type: "answer", text: answer });
    }

    // Read from the original message, so code inside the block keeps its bytes.
    const reasoning = message
      .slice(start + opening.length, end - closing.length)
      .trim();
    if (reasoning !== "") {
      segments.push({ type: "reasoning", text: reasoning });
    }

    cursor = end;
  }

  const rest = message.slice(cursor);
  if (rest !== "") {
    segments.push({ type: "answer", text: rest });
  }
  return segments;
};

// Whether a segment is worth rendering: reasoning text is already trimmed and a
// blank answer fragment is skipped. Non-string data is rendered as it arrived.
const hasVisibleContent = (segment) =>
  segment.type === "reasoning" ||
  typeof segment.text !== "string" ||
  segment.text.trim() !== "";

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

function ReasoningAccordion({ text, label }) {
  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={{
        mb: 1.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 1,
        bgcolor: "transparent",
        "&::before": { display: "none" },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon fontSize="small" />}
        sx={{ minHeight: 0, "& .MuiAccordionSummary-content": { my: 1 } }}
      >
        <Typography variant="subtitle2" color="text.secondary">
          {label}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0 }}>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
        >
          {text}
        </Typography>
      </AccordionDetails>
    </Accordion>
  );
}

export function TextMessage({ message, isError = false, isUser = false }) {
  const { t } = useTranslation("generative");
  // Reasoning tags only come from the model, so a user message is kept as
  // written. Segments render in their original order.
  const segments = (
    isUser ? [{ type: "answer", text: message }] : splitReasoning(message)
  ).filter(hasVisibleContent);

  return (
    <Box>
      {segments.map((segment, index) =>
        segment.type === "reasoning" ? (
          <ReasoningAccordion
            key={`reasoning-${index}`}
            text={segment.text}
            label={t("textMessage.reasoning")}
          />
        ) : (
          <Typography
            key={`answer-${index}`}
            variant="body1"
            component="div"
            color={isError ? "red" : "text.primary"}
            sx={{ overflowWrap: "anywhere" }}
          >
            <Markdown
              remarkPlugins={remarkPlugins}
              components={markdownComponents}
            >
              {segment.text}
            </Markdown>
          </Typography>
        ),
      )}
    </Box>
  );
}
