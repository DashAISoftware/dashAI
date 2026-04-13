import { useState } from "react";
import { Box, IconButton, Tooltip, Typography, useTheme } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import Markdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  oneDark,
  oneLight,
} from "react-syntax-highlighter/dist/esm/styles/prism";

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <Tooltip title={copied ? "Copied!" : "Copy"}>
      <IconButton
        size="small"
        onClick={handleCopy}
        sx={{ color: "grey.400", "&:hover": { color: "grey.100" } }}
      >
        {copied ? (
          <CheckIcon fontSize="inherit" />
        ) : (
          <ContentCopyIcon fontSize="inherit" />
        )}
      </IconButton>
    </Tooltip>
  );
}

function CodeBlock({ language, children }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const code = String(children).replace(/\n$/, "");

  return (
    <Box
      sx={{
        borderRadius: 1,
        overflow: "hidden",
        my: 1,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 1.5,
          py: 0.5,
          bgcolor: isDark ? "grey.900" : "grey.200",
        }}
      >
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {language || "code"}
        </Typography>
        <CopyButton text={code} />
      </Box>
      <SyntaxHighlighter
        language={language || "text"}
        style={isDark ? oneDark : oneLight}
        customStyle={{ margin: 0, borderRadius: 0, fontSize: "0.85em" }}
        PreTag="div"
      >
        {code}
      </SyntaxHighlighter>
    </Box>
  );
}

export function TextMessage({ message, isError = false }) {
  return (
    <Box>
      <Typography
        variant="body2"
        component="div"
        color={isError ? "red" : "text.primary"}
      >
        <Markdown
          components={{
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              if (!inline) {
                return (
                  <CodeBlock language={match ? match[1] : null}>
                    {children}
                  </CodeBlock>
                );
              }
              return (
                <Box
                  component="code"
                  sx={{
                    px: 0.5,
                    py: 0.1,
                    borderRadius: 0.5,
                    bgcolor: "action.hover",
                    fontSize: "0.85em",
                  }}
                  {...props}
                >
                  {children}
                </Box>
              );
            },
          }}
        >
          {message}
        </Markdown>
      </Typography>
    </Box>
  );
}
