import { Box, Typography, useTheme } from "@mui/material";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  oneDark,
  oneLight,
} from "react-syntax-highlighter/dist/esm/styles/prism";
import { CopyButton } from "./CopyButton";

export function CodeBlock({ language, children }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const code = String(children).replace(/\n$/, "");

  return (
    <Box
      sx={{
        borderRadius: 1,
        overflow: "hidden",
        my: 2,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 3,
          py: 1,
          bgcolor: isDark ? "grey.900" : "grey.200",
        }}
      >
        <Typography variant="code" sx={{ color: "text.secondary" }}>
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
