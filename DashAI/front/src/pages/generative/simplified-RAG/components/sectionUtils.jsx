import { Box } from "@mui/material";

export const getDescription = (desc, i18n) => {
  if (!desc) return "";
  if (typeof desc === "string") return desc;
  if (typeof desc === "object" && (desc.en || desc.es)) {
    return desc[i18n.language] || desc.en || desc.es || "";
  }
  return "";
};

/**
 * Render a template string with placeholders ({chunks}, {input}, etc.) highlighted.
 *
 * @param {string} template - The template string to render
 * @param {object}  [highlightColors] - Optional resolved color overrides (hex/rgba)
 * @param {string} [highlightColors.bg] - Background color for placeholders
 * @param {string} [highlightColors.text] - Text color for placeholders
 */
export const renderTemplateWithHighlights = (template, highlightColors = {}) => {
  if (!template) return null;

  const { bg, text } = highlightColors;

  const placeholderRegex = /\{([^}]+)\}/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = placeholderRegex.exec(template)) !== null) {
    if (match.index > lastIndex) {
      parts.push(template.substring(lastIndex, match.index));
    }

    parts.push({
      type: "placeholder",
      value: match[0],
      label: match[1],
    });

    lastIndex = placeholderRegex.lastIndex;
  }

  if (lastIndex < template.length) {
    parts.push(template.substring(lastIndex));
  }

  return parts.map((part, idx) => {
    if (typeof part === "string") {
      return <span key={idx}>{part}</span>;
    }
    return (
      <Box
        component="span"
        key={idx}
        sx={{
          backgroundColor: bg || "warning.light",
          color: text || "warning.dark",
          padding: "2px 4px",
          borderRadius: "3px",
          fontWeight: 600,
          fontFamily: "monospace",
        }}
      >
        {part.value}
      </Box>
    );
  });
};
