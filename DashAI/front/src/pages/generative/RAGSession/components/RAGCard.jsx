import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Typography,
  Tooltip,
  IconButton,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import PropTypes from "prop-types";

/**
 * An accordion card for a single RAG configuration section (documents, chunking,
 * retriever, etc.). Supports optional action buttons in the header.
 *
 * @param {object}          props
 * @param {string}          props.title         - Card title.
 * @param {boolean}         props.expanded      - Whether the accordion is expanded.
 * @param {Function}        props.onChange      - Accordion change handler.
 * @param {Array}           [props.actions]     - Header action buttons ({ icon, tooltip, onClick, ariaLabel }).
 * @param {React.ReactNode} [props.children]    - Accordion content.
 * @returns {JSX.Element} The accordion card.
 */
export default function RAGCard({
  title,
  expanded,
  onChange,
  actions = [],
  children,
}) {
  return (
    <Accordion
      expanded={expanded}
      onChange={onChange}
      sx={{
        "&::before": {
          display: "none",
        },
        "&.Mui-expanded": {
          marginTop: 0,
          marginBottom: 0,
        },
        px: 4,
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          minHeight: 48,
          "&.Mui-expanded": {
            minHeight: 48,
          },
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
          }}
        >
          <Typography variant="subtitle1">{title}</Typography>
          {actions.length > 0 && (
            <Box sx={{ display: "flex" }}>
              {actions.map((action, index) => (
                <Tooltip key={index} title={action.tooltip}>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      action.onClick?.();
                    }}
                    aria-label={action.ariaLabel || ""}
                  >
                    {action.icon}
                  </IconButton>
                </Tooltip>
              ))}
            </Box>
          )}
        </Box>
      </AccordionSummary>
      <AccordionDetails
        sx={{
          display: "flex",
          flexDirection: "column",
          pt: 0,
        }}
      >
        {children}
      </AccordionDetails>
    </Accordion>
  );
}

RAGCard.propTypes = {
  title: PropTypes.string.isRequired,
  expanded: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  actions: PropTypes.arrayOf(
    PropTypes.shape({
      icon: PropTypes.node.isRequired,
      tooltip: PropTypes.string,
      onClick: PropTypes.func,
      ariaLabel: PropTypes.string,
    }),
  ),
  children: PropTypes.node,
};
