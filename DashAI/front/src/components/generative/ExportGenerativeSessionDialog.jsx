import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  IconButton,
  Modal,
  Typography,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import {
  exportGenerativeSession,
  getGenerativeSessionExportPreview,
} from "../../api/session";
import { getApiErrorMessageAsync } from "../../utils/apiError";
import { triggerDownload } from "../../utils/downloadArtifact";
import { formatBytes, sessionFilename } from "../../utils/sessionFile";

/**
 * Download a generative session as a .dashai file, with or without its
 * conversation.
 *
 * The configuration always travels. The conversation is opt-in: it may hold
 * content the user does not mean to share, and its images or videos can make
 * the file large. Messages still running or that failed are never exported.
 */
export default function ExportGenerativeSessionDialog({
  open,
  sessionId,
  onClose,
}) {
  const { t } = useTranslation(["generative", "models", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const [preview, setPreview] = useState(null);
  const [includeConversation, setIncludeConversation] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!open || sessionId == null) return;
    let cancelled = false;
    setPreview(null);
    setIncludeConversation(false);
    getGenerativeSessionExportPreview(sessionId)
      .then((data) => {
        if (!cancelled) setPreview(data);
      })
      .catch(() => {
        if (cancelled) return;
        enqueueSnackbar(t("generative:error.loadExportPreview"), {
          variant: "error",
        });
        onClose();
      });
    return () => {
      cancelled = true;
    };
    // Reload only when the target changes; onClose and t do not matter here.
  }, [open, sessionId]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await exportGenerativeSession(sessionId, {
        includeConversation,
      });
      triggerDownload(blob, sessionFilename(preview.session_name));
      onClose();
    } catch (error) {
      const reason = await getApiErrorMessageAsync(error);
      const message = t("generative:error.exportSession");
      enqueueSnackbar(reason ? `${message}: ${reason}` : message, {
        variant: "error",
      });
    } finally {
      setExporting(false);
    }
  };

  const hasMessages = preview?.message_count > 0;
  const size =
    (preview?.documents_size_bytes || 0) +
    (includeConversation ? preview?.media_size_bytes || 0 : 0);

  return (
    <Modal open={open} onClose={onClose}>
      <Box
        onClick={(e) => e.stopPropagation()}
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: { xs: "90%", sm: 480 },
          bgcolor: "background.paper",
          borderRadius: 2,
          boxShadow: 12,
          outline: "none",
        }}
      >
        <Box
          sx={{
            p: 2,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="h6" component="h2">
            {t("models:label.exportSessionTitle", {
              name: preview?.session_name || "",
            })}
          </Typography>
          <IconButton
            onClick={onClose}
            size="small"
            aria-label={t("common:close")}
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {!preview ? (
          <Box sx={{ p: 4, display: "flex", justifyContent: "center" }}>
            <CircularProgress size={28} />
          </Box>
        ) : (
          <Box
            sx={{
              p: 3,
              pt: 0,
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {t("generative:label.exportConfigurationAlways")}
            </Typography>

            {preview.document_count > 0 && (
              <Alert severity="info">
                {t("generative:label.exportIncludesDocuments", {
                  count: preview.document_count,
                })}
              </Alert>
            )}

            <Box>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={includeConversation}
                    disabled={!hasMessages}
                    onChange={(e) => setIncludeConversation(e.target.checked)}
                  />
                }
                label={t("generative:label.includeConversation", {
                  count: preview.message_count,
                })}
              />
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                {hasMessages
                  ? t("generative:label.includeConversationHelp")
                  : t("generative:label.noConversation")}
              </Typography>
            </Box>

            {includeConversation && preview.unfinished_count > 0 && (
              <Alert severity="info">
                {t("generative:label.unfinishedNotExported", {
                  count: preview.unfinished_count,
                })}
              </Alert>
            )}

            {size > 0 && (
              <Alert severity="info">
                {t("models:label.approxSize", { size: formatBytes(size) })}
              </Alert>
            )}

            <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 2 }}>
              <Button onClick={onClose} sx={{ color: "text.secondary" }}>
                {t("common:cancel")}
              </Button>
              <Button
                variant="contained"
                onClick={handleExport}
                disabled={exporting}
                startIcon={
                  exporting ? (
                    <CircularProgress size={16} color="inherit" />
                  ) : null
                }
              >
                {t("common:export")}
              </Button>
            </Box>
          </Box>
        )}
      </Box>
    </Modal>
  );
}

ExportGenerativeSessionDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  sessionId: PropTypes.number,
  onClose: PropTypes.func.isRequired,
};
