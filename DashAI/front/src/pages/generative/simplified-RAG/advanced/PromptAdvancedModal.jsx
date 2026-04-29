import { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  Box,
  Typography,
  Paper,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

export default function PromptAdvancedModal({
  open,
  onClose,
  selectedPrompt,
  promptId,
  setPromptId,
}) {
  const handleClose = () => {
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          maxHeight: "90vh",
          zIndex: 1300,
        },
      }}
      BackdropProps={{
        sx: {
          zIndex: 1299,
        }
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        Advanced Prompt Configuration
        <IconButton
          onClick={handleClose}
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ minHeight: 400 }}>
        <Box display="flex" flexDirection="column" gap={2}>
          <Paper sx={{ p: 2, backgroundColor: "action.hover" }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              {selectedPrompt?.name}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {selectedPrompt?.description || "No description available"}
            </Typography>
          </Paper>

          {selectedPrompt?.template && (
            <Paper sx={{ p: 2, backgroundColor: "background.default" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                Prompt Template
              </Typography>
              <Typography
                variant="body2"
                component="pre"
                sx={{
                  fontFamily: "monospace",
                  fontSize: "0.75rem",
                  overflow: "auto",
                  maxHeight: 300,
                  p: 1,
                  backgroundColor: "background.paper",
                  borderRadius: 1,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                {selectedPrompt.template}
              </Typography>
            </Paper>
          )}

          <Box sx={{ color: "text.secondary" }}>
            <Typography variant="caption">
              Advanced configuration for prompts is typically managed through
              the prompt templates interface. You can create custom prompts or
              modify existing ones there.
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={handleClose} color="inherit">
          Close
        </Button>
        <Button
          onClick={handleClose}
          variant="contained"
          color="primary"
        >
          Done
        </Button>
      </DialogActions>
    </Dialog>
  );
}
