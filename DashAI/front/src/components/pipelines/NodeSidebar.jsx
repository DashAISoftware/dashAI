import React from "react";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { getNodeHelp } from "./nodeHelp";

function NodeSidebar({ availableNodes, onDragStart, nodeHelp }) {
  const theme = useTheme();
  return (
    <Box
      sx={{
        width: 250,
        p: 2,
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
      {availableNodes.map((node) => (
        <Box
          key={node.type}
          onDragStart={(e) => onDragStart(e, node.type)}
          draggable
          sx={{
            mb: 1,
            p: 1,
            backgroundColor: theme.palette.ui.border,
            color: theme.palette.text.primary,
            borderRadius: 1,
            textAlign: "center",
            cursor: "grab",
          }}
        >
          <Typography>{node.name || node.type}</Typography>
        </Box>
      ))}

      <Box
        sx={{
          p: 2,
          borderTop: `1px solid ${theme.palette.ui.borderLight}`,
          backgroundColor: theme.palette.background.box,
          mt: 2,
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
                  gap: 1,
                }}
              >
                <HelpOutlineIcon fontSize="inherit" sx={{ mt: 0.8 }} />
                {help.name || nodeHelp?.type || "Pipeline Help"}
              </Typography>
              {help.description && (
                <>
                  {help.description.split("\n").map((paragraph) => (
                    <Typography
                      key={paragraph}
                      variant="body1"
                      sx={{ mb: 1, color: theme.palette.text.secondary }}
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
