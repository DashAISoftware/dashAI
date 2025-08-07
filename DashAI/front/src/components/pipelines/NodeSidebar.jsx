import React from "react";
import { Box, Typography } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { getNodeHelp } from ".";

function NodeSidebar({ availableNodes, onDragStart, nodeHelp }) {
  return (
    <Box
      sx={{ width: 250, p: 2, backgroundColor: "#212121", overflowY: "auto" }}
    >
      <Typography variant="h6" gutterBottom sx={{ color: "#fff" }}>
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
            backgroundColor: "#333",
            color: "#fff",
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
          borderTop: "1px solid #ccc",
          backgroundColor: "#212121",
          mt: 2,
        }}
      >
        {(() => {
          const help = getNodeHelp(nodeHelp?.type || "Pipeline");
          return (
            <>
              <Typography
                variant="h6"
                sx={{ color: "#fff", display: "flex", gap: 1 }}
              >
                <HelpOutlineIcon fontSize="inherit" sx={{ mt: 0.8 }} />
                {help.name || nodeHelp?.type || "Pipeline Help"}
              </Typography>
              {help.description && (
                <>
                  {help.description.split("\n").map((paragraph, idx) => (
                    <Typography
                      key={idx}
                      variant="body1"
                      sx={{ mb: 1, color: "#ddd" }}
                    >
                      {paragraph}
                    </Typography>
                  ))}
                </>
              )}
              {help.input && (
                <Typography variant="body2" sx={{ color: "#ccc" }}>
                  <u>Inputs:</u> {help.input || "None"}
                </Typography>
              )}
              {help.output && (
                <Typography variant="body2" sx={{ color: "#ccc" }}>
                  <u>Outputs:</u> {help.output || "None"}
                </Typography>
              )}
              {help.next && (
                <Typography variant="body2" sx={{ color: "#ccc" }}>
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
