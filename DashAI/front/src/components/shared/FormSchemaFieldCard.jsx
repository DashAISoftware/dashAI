import { Avatar, Box, Link, Paper, Typography } from "@mui/material";
import PropTypes from "prop-types";
import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import { FormCardProvider } from "../../contexts/FormCardContext";

const AVATAR_COLORS = [
  "#5C6BC0",
  "#26A69A",
  "#7E57C2",
  "#29B6F6",
  "#66BB6A",
  "#FFA726",
  "#EF5350",
  "#8D6E63",
];

const CHAR_LIMIT = 120;

function charHashColor(str = "") {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) & 0xffffffff;
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

// Markdown component overrides — render with caption sizing and theme colours
const mdComponents = (color) => ({
  p: ({ children }) => (
    <Typography
      component="span"
      variant="caption"
      color={color}
      sx={{ display: "block", lineHeight: 1.5, "& + span": { mt: 0.25 } }}
    >
      {children}
    </Typography>
  ),
  a: ({ href, children }) => (
    <Link
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      variant="caption"
      color="primary"
    >
      {children}
    </Link>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <Box
        component="code"
        sx={{
          fontFamily: "monospace",
          fontSize: "0.7rem",
          bgcolor: "action.hover",
          borderRadius: 0.5,
          px: 0.4,
          py: 0.1,
        }}
      >
        {children}
      </Box>
    ) : (
      <Box
        component="pre"
        sx={{
          fontFamily: "monospace",
          fontSize: "0.7rem",
          bgcolor: "action.hover",
          borderRadius: 1,
          p: 0.75,
          mt: 0.5,
          overflowX: "auto",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        <code>{children}</code>
      </Box>
    ),
  strong: ({ children }) => (
    <Box component="strong" sx={{ fontWeight: 700 }}>
      {children}
    </Box>
  ),
  em: ({ children }) => (
    <Box component="em" sx={{ fontStyle: "italic" }}>
      {children}
    </Box>
  ),
  ul: ({ children }) => (
    <Box
      component="ul"
      sx={{ pl: 2, my: 0.25, "& li": { fontSize: "0.75rem" } }}
    >
      {children}
    </Box>
  ),
  ol: ({ children }) => (
    <Box
      component="ol"
      sx={{ pl: 2, my: 0.25, "& li": { fontSize: "0.75rem" } }}
    >
      {children}
    </Box>
  ),
});

function DescriptionBlock({ text, isError }) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslation(["common"]);

  if (!text) return null;

  const needsTruncation = text.length > CHAR_LIMIT;
  const displayed =
    expanded || !needsTruncation ? text : `${text.slice(0, CHAR_LIMIT)}\u2026`;
  const color = isError ? "error.main" : "text.disabled";

  return (
    <Box sx={{ mt: 0.5, pb: 0.5 }}>
      <ReactMarkdown components={mdComponents(color)}>
        {displayed}
      </ReactMarkdown>
      {needsTruncation && (
        <Link
          component="button"
          type="button"
          variant="caption"
          color={isError ? "error" : "primary"}
          underline="hover"
          onClick={() => setExpanded((prev) => !prev)}
          sx={{
            mt: 0.25,
            display: "inline-block",
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
        >
          {expanded ? t("common:viewLess") : t("common:viewMore")}
        </Link>
      )}
    </Box>
  );
}

DescriptionBlock.propTypes = {
  text: PropTypes.string,
  isError: PropTypes.bool,
};

/**
 * Card shell used by all FormSchema field variants.
 * Renders a header row (avatar + label + param key + optional right slot)
 * and a body with the input(s) followed by an inline truncated description.
 *
 * @param {string} label        - Display label shown bold in the header
 * @param {string} paramKey     - Technical key shown in monospace below the label
 * @param {string} description  - Parameter description shown inline below the input
 * @param {string} errorMessage - When set, replaces description and renders in red
 * @param {node}   headerRight  - Optional right-side header slot (optimize toggle, expand button…)
 * @param {node}   children     - The actual input(s)
 */
function FormSchemaFieldCard({
  label,
  paramKey,
  description,
  errorMessage,
  headerRight,
  children,
}) {
  const avatarLetter = (label || paramKey || "?")[0].toUpperCase();
  const avatarBg = charHashColor(paramKey || label || "");

  return (
    <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden" }}>
      {/* ── Header ── */}
      <Box
        sx={{
          px: 2,
          py: 0.75,
          display: "flex",
          alignItems: "center",
          gap: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Avatar
          sx={{
            width: 26,
            height: 26,
            bgcolor: avatarBg,
            fontSize: 12,
            flexShrink: 0,
          }}
        >
          {avatarLetter}
        </Avatar>

        <Box flex={1} minWidth={0}>
          <Typography
            variant="body2"
            fontWeight={600}
            color={errorMessage ? "error.main" : "text.primary"}
          >
            {label}
          </Typography>
          {paramKey && paramKey !== label && (
            <Typography
              component="span"
              variant="caption"
              color="text.secondary"
              sx={{ fontFamily: "monospace" }}
            >
              {paramKey}
            </Typography>
          )}
        </Box>

        {headerRight}
      </Box>

      {/* ── Body ── */}
      <FormCardProvider>
        <Box
          sx={{
            px: 2,
            pt: 0.5,
            pb: description || errorMessage ? 0.5 : 1,
            // Hide the floating label — the card header already shows it
            "& .MuiInputLabel-root": { display: "none" },
            // Remove the label notch indent from outlined inputs
            "& .MuiOutlinedInput-notchedOutline legend > span": {
              display: "none",
            },
          }}
        >
          {children}
        </Box>

        {(description || errorMessage) && (
          <Box sx={{ px: 2 }}>
            <DescriptionBlock
              text={errorMessage ?? description}
              isError={Boolean(errorMessage)}
            />
          </Box>
        )}
      </FormCardProvider>
    </Paper>
  );
}

FormSchemaFieldCard.propTypes = {
  label: PropTypes.string,
  paramKey: PropTypes.string,
  description: PropTypes.string,
  errorMessage: PropTypes.string,
  headerRight: PropTypes.node,
  children: PropTypes.node.isRequired,
};

export default FormSchemaFieldCard;
