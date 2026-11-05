import PropTypes from "prop-types";
import { Link } from "@mui/material";

const URL_PATTERN = /(\[([^\]]+)\]\((https?:\/\/[^)]+)\))|(https?:\/\/\S+)/g;
const TRAILING_PUNCT = /[.,;:!?)\]>'"]+$/;

function DescriptionText({ text }) {
  if (!text) return null;
  const parts = [];
  let last = 0;
  let match;
  URL_PATTERN.lastIndex = 0;
  while ((match = URL_PATTERN.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[1]) {
      parts.push(
        <Link
          key={match.index}
          href={match[3]}
          target="_blank"
          rel="noopener noreferrer"
        >
          {match[2]}
        </Link>,
      );
    } else {
      const rawUrl = match[0];
      const cleanUrl = rawUrl.replace(TRAILING_PUNCT, "");
      const trailing = rawUrl.slice(cleanUrl.length);
      parts.push(
        <Link
          key={match.index}
          href={cleanUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          {cleanUrl}
        </Link>,
      );
      if (trailing) parts.push(trailing);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

DescriptionText.propTypes = {
  text: PropTypes.string,
};

export default DescriptionText;
