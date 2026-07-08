import React from "react";
import { Box, IconButton, Tooltip, Typography } from "@mui/material";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

/**
 * Displays a list of required placeholders with icons and a "+" button
 * to insert each placeholder into the prompt template textarea.
 */
export default function PlaceholdersList({
  required = [],
  descriptions = {},
  template = "",
  onInsertPlaceholder,
}) {
  return (
    <Box sx={{ mt: 2, mb: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Required Placeholders
      </Typography>
      <Box
        component="ul"
        sx={{
          listStyle: "none",
          m: 0,
          p: 0,
          display: "flex",
          flexDirection: "column",
          gap: 0.5,
        }}
      >
        {required.map((ph) => {
          const isPresent = template.includes(ph);
          return (
            <Box
              component="li"
              key={ph}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
              }}
            >
              {/* Status icon */}
              {isPresent ? (
                <CheckCircleIcon
                  fontSize="small"
                  color="success"
                  sx={{ flexShrink: 0 }}
                />
              ) : (
                <WarningAmberIcon
                  fontSize="small"
                  color="warning"
                  sx={{ flexShrink: 0 }}
                />
              )}

              {/* Insert button */}
              {onInsertPlaceholder && (
                <Tooltip title={`Insert ${ph}`} placement="top">
                  <IconButton
                    size="small"
                    onClick={() => onInsertPlaceholder(ph)}
                    sx={{
                      p: 0.25,
                      color: "primary.main",
                      "&:hover": { backgroundColor: "primary.light" },
                    }}
                  >
                    <AddCircleOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}

              {/* Placeholder text */}
              <Typography
                component="code"
                variant="body2"
                sx={{
                  fontFamily: "monospace",
                  fontWeight: 600,
                  fontSize: "0.8rem",
                }}
              >
                {ph}
              </Typography>

              {/* Info tooltip */}
              {descriptions[ph] && (
                <Tooltip title={descriptions[ph]} placement="right">
                  <HelpOutlineIcon
                    fontSize="small"
                    color="action"
                    sx={{ cursor: "pointer", flexShrink: 0 }}
                  />
                </Tooltip>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
