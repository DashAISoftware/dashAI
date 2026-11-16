import React from "react";
import PropTypes from "prop-types";
import { Box, Link, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslation } from "react-i18next";
import { resolveReadmeUrl } from "../pluginUtils";

const mono = { fontFamily: '"Geist Mono", monospace' };

// A plugin's README.md as GitHub shows it, relative URLs from urls
export default function Readme({ text, urls = null }) {
  const { t } = useTranslation(["plugins"]);
  const theme = useTheme();
  if (!text) {
    return (
      <Typography sx={{ color: "text.secondary" }}>
        {t("plugins:detail.noReadme")}
      </Typography>
    );
  }
  const urlTransform = (url, key) => {
    if (key !== "src") return resolveReadmeUrl(url, urls?.links);
    const image = resolveReadmeUrl(url, urls?.images);
    return image?.startsWith("https:") ? image : null;
  };
  return (
    <Box
      sx={{
        // No gap above its title, first-child is unsafe with Emotion
        "& > h1:first-of-type": { mt: 0 },
        "& h1, & h2, & h3": { fontWeight: 600, mt: 3, mb: 1 },
        "& h1": { fontSize: 22 },
        "& h2": { fontSize: 19 },
        "& h3": { fontSize: 17 },
        "& p, & li": { fontSize: 14, lineHeight: 1.7 },
        "& code": {
          ...mono,
          fontSize: 12,
          bgcolor: theme.palette.ui.box,
          px: 0.5,
          borderRadius: 0.5,
        },
        "& pre": {
          bgcolor: theme.palette.ui.box,
          p: 2,
          borderRadius: 1,
          overflow: "auto",
        },
        "& pre code": { bgcolor: "transparent", p: 0 },
        "& table": { borderCollapse: "collapse", my: 2, fontSize: 13 },
        "& th, & td": {
          border: `1px solid ${theme.palette.ui.border}`,
          px: 1.5,
          py: 0.75,
        },
        "& img": { maxWidth: "100%" },
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={urlTransform}
        components={{
          // Outside the app, so a README link never replaces dashAI.
          a: ({ node, ...props }) => (
            <Link {...props} target="_blank" rel="noopener noreferrer" />
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </Box>
  );
}
Readme.propTypes = {
  text: PropTypes.string,
  urls: PropTypes.shape({
    images: PropTypes.string.isRequired,
    links: PropTypes.string.isRequired,
  }),
};
