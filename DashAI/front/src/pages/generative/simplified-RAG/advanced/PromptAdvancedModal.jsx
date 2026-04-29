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
import { useTranslation } from "react-i18next";

export default function PromptAdvancedModal({
  open,
  onClose,
  selectedPrompt,
  promptId,
  setPromptId,
}) {
  const { t } = useTranslation(["generative"]);
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
        {t("generative:simplifiedRag.advanced.promptTitle")}
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
              {selectedPrompt?.description || t("generative:simplifiedRag.advanced.noDescription")}
            </Typography>
          </Paper>

          {selectedPrompt?.template && (
            <Paper sx={{ p: 2, backgroundColor: "background.default" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                {t("generative:simplifiedRag.advanced.promptTemplate")}
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
              {t("generative:simplifiedRag.advanced.promptInfo")}
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={handleClose} color="inherit">
          {t("generative:simplifiedRag.advanced.close")}
        </Button>
        <Button
          onClick={handleClose}
          variant="contained"
          color="primary"
        >
          {t("generative:simplifiedRag.advanced.done")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

