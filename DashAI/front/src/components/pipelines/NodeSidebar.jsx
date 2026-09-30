import React from "react";
import { Box, Typography } from "@mui/material";
import { useTheme, alpha } from "@mui/material/styles";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { getNodeHelp } from "./nodeHelp";

/**
 * NodeSidebar – draggable node palette + contextual help.
 *
 * Highlighting props make pipeline construction more intuitive without ever
 * restricting what can be dragged:
 *   - highlightMode "start": the canvas is empty; root nodes (the ones that can
 *     open a flow) are emphasized as the suggested starting point.
 *   - highlightMode "successors": a node is focused on the canvas; the nodes
 *     that can legally come after it are emphasized and the rest are dimmed.
 * The set of emphasized node types is passed in `highlightedTypes`. Non-matching
 * nodes stay fully draggable — they are only visually de-emphasized.
 */
function NodeSidebar({
  availableNodes,
  onDragStart,
  nodeHelp,
  highlightMode = null,
  highlightedTypes = [],
  highlightLabel = "",
}) {
  const theme = useTheme();

  const highlightActive = Boolean(highlightMode) && highlightedTypes.length > 0;
  const highlightSet = new Set(highlightedTypes);
  const accentColor =
    highlightMode === "start"
      ? theme.palette.success.main
      : theme.palette.primary.main;

  return (
    <Box
      sx={{
        width: 250,
        p: 4,
        backgroundColor: theme.palette.background.box,
        overflowY: "auto",
      }}
    >
      <Typography
        variant="h6"
        gutterBottom
        sx={{ color: theme.palette.text.primary }}
      >
        Nodes
      </Typography>

      {highlightActive && highlightLabel && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            mb: 2,
            px: 1.5,
            py: 1,
            borderRadius: 1,
            backgroundColor: alpha(accentColor, 0.12),
            border: `1px solid ${alpha(accentColor, 0.5)}`,
          }}
        >
          {highlightMode === "start" ? (
            <PlayArrowIcon sx={{ fontSize: 18, color: accentColor }} />
          ) : (
            <ArrowForwardIcon sx={{ fontSize: 18, color: accentColor }} />
          )}
          <Typography
            variant="caption"
            sx={{ color: theme.palette.text.primary, fontWeight: 600 }}
          >
            {highlightLabel}
          </Typography>
        </Box>
      )}

      {availableNodes.map((node) => {
        const isHighlighted = highlightActive && highlightSet.has(node.type);
        const isDimmed = highlightActive && !isHighlighted;

        return (
          <Box
            key={node.type}
            onDragStart={(e) => onDragStart(e, node.type)}
            draggable
            sx={{
              mb: 2,
              p: 2,
              backgroundColor: isHighlighted
                ? alpha(accentColor, 0.16)
                : theme.palette.ui.border,
              color: theme.palette.text.primary,
              borderRadius: 1,
              textAlign: "center",
              cursor: "grab",
              border: isHighlighted
                ? `2px solid ${accentColor}`
                : "2px solid transparent",
              boxShadow: isHighlighted
                ? `0 0 8px ${alpha(accentColor, 0.5)}`
                : "none",
              opacity: isDimmed ? 0.35 : 1,
              transition:
                "opacity 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease",
            }}
          >
            <Typography>{node.name || node.type}</Typography>
          </Box>
        );
      })}

      <Box
        sx={{
          p: 4,
          borderTop: `1px solid ${theme.palette.ui.borderLight}`,
          backgroundColor: theme.palette.background.box,
          mt: 4,
        }}
      >
        {(() => {
          const help = getNodeHelp(nodeHelp?.type || "Pipeline");
          return (
            <>
              <Typography
                variant="h6"
                sx={{
                  color: theme.palette.text.primary,
                  display: "flex",
                  gap: 2,
                }}
              >
                <HelpOutlineIcon fontSize="inherit" sx={{ mt: 2 }} />
                {help.name || nodeHelp?.type || "Pipeline Help"}
              </Typography>
              {help.description && (
                <>
                  {help.description.split("\n").map((paragraph, idx) => (
                    <Typography
                      key={idx}
                      variant="body1"
                      sx={{ mb: 2, color: theme.palette.text.secondary }}
                    >
                      {paragraph}
                    </Typography>
                  ))}
                </>
              )}
              {help.input && (
                <Typography
                  variant="body2"
                  sx={{ color: theme.palette.text.secondary }}
                >
                  <u>Inputs:</u> {help.input || "None"}
                </Typography>
              )}
              {help.output && (
                <Typography
                  variant="body2"
                  sx={{ color: theme.palette.text.secondary }}
                >
                  <u>Outputs:</u> {help.output || "None"}
                </Typography>
              )}
              {help.next && (
                <Typography
                  variant="body2"
                  sx={{ color: theme.palette.text.secondary }}
                >
                  <u>Can be followed by:</u> {help.next || "None"}
                </Typography>
              )}
            </>
          );
        })()}
      </Box>
    </Box>
  );
}

export default NodeSidebar;
