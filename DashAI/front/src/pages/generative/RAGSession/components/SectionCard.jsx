import { Box } from "@mui/material";
import PropTypes from "prop-types";
import { useTheme } from "@mui/material/styles";

/**
 * Wrapper box for a single section inside a RAGCard accordion.
 * Provides consistent gap and flex-column layout.
 *
 * @param {object}          props
 * @param {React.ReactNode} [props.children]     - Content to render.
 * @param {object|Array}    [props.sx]           - Additional MUI sx overrides.
 * @param {number|string}   [props.gap]          - Gap between children (default 0).
 * @param {string}          [props.alignItems]   - Flex align-items (default "stretch").
 * @param {string}          [props.justifyContent] - Flex justify-content.
 * @returns {JSX.Element} The section wrapper.
 */
export default function SectionCard({
  children,
  sx,
  gap = 0,
  alignItems = "stretch",
  justifyContent,
}) {
  const theme = useTheme();
  const sectionGap = typeof gap === "number" ? theme.spacing(gap) : gap;

  return (
    <Box
      sx={[
        {
          "--rag-section-gap": sectionGap,
          display: "flex",
          flexDirection: "column",
          gap,
          alignItems,
          justifyContent,
          pt: 0,
          pb: 3,
        },
        sx,
      ]}
    >
      {children}
    </Box>
  );
}

SectionCard.propTypes = {
  children: PropTypes.node,
  sx: PropTypes.oneOfType([PropTypes.array, PropTypes.object, PropTypes.func]),
  gap: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  alignItems: PropTypes.oneOf([
    "stretch",
    "flex-start",
    "center",
    "flex-end",
    "baseline",
  ]),
  justifyContent: PropTypes.oneOf([
    "flex-start",
    "center",
    "flex-end",
    "space-between",
    "space-around",
    "space-evenly",
  ]),
};
