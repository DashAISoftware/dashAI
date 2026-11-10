import { useId } from "react";
import {
  Alert,
  Box,
  Button,
  IconButton,
  Modal,
  Typography,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

/**
 * Confirmation dialog for a destructive action.
 *
 * The confirm button is never focused on open: a user who dismisses a stray
 * dialog with Enter/Space must not delete the item, so the safe action
 * (Cancel) takes the initial focus. Every action also carries a stable key, so
 * a re-render that reveals the secondary action cannot hand an already-focused
 * node a different meaning.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is visible.
 * @param {Function} props.onClose - Dismisses the dialog.
 * @param {Function} [props.onConfirm] - Runs the destructive action.
 * @param {string}   [props.content] - Body text for the dialog.
 * @param {string}   [props.warning] - Extra warning shown under the body.
 * @param {string}   [props.warningSeverity="error"] - Severity of the warning.
 * @param {Function} [props.onExited] - Called once the modal has closed.
 * @param {string}   [props.confirmLabel] - Label of the destructive action.
 * @param {Function} [props.onSecondary] - Runs an alternative action.
 * @param {string}   [props.secondaryLabel] - Label of the alternative action.
 * @param {string}   [props.confirmVariant="text"] - Emphasis of the confirm
 *   button; a caller with a riskier secondary action can demote it.
 * @param {string}   [props.secondaryVariant="outlined"] - Emphasis of the
 *   secondary button; the safer action can be promoted.
 * @param {boolean}  [props.deleting=false] - Disables every action while a
 *   request is in flight.
 * @returns {JSX.Element} The confirmation dialog.
 */
export default function DeleteConfirmationModal({
  open,
  onClose,
  onConfirm,
  content,
  warning,
  warningSeverity = "error",
  onExited,
  confirmLabel,
  onSecondary,
  secondaryLabel,
  confirmVariant = "text",
  secondaryVariant = "outlined",
  deleting = false,
}) {
  const { t } = useTranslation(["common"]);
  const titleId = useId();
  // Every action shares one layout so the buttons wrap instead of overflowing
  // on a narrow dialog.
  const actionSx = { flex: { xs: "1 1 100%", sm: "0 0 auto" } };

  return (
    <Modal
      open={open}
      onClose={deleting ? undefined : onClose}
      slotProps={{ transition: { onExited } }}
    >
      <Box
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        // The modal is portaled but React still bubbles events through the
        // component tree, so without this a click inside it would reach an
        // ancestor's onClick (e.g. a clickable model row) and trigger it.
        onClick={(e) => e.stopPropagation()}
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: { xs: "90%", sm: 560 },
          bgcolor: "background.paper",
          borderRadius: 2,
          boxShadow: 12,
          p: 0,
          outline: "none",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography id={titleId} variant="h6" component="h2">
            {t("common:confirmDeletion")}
          </Typography>
          <IconButton
            onClick={onClose}
            size="small"
            disabled={deleting}
            aria-label={t("common:close")}
            sx={{ color: "text.secondary" }}
          >
            <Close />
          </IconButton>
        </Box>

        {/* Content */}
        <Box sx={{ p: 3, display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography
            variant="body1"
            sx={{ whiteSpace: "pre-line" }}
            color="text.secondary"
          >
            {content ||
              t(
                "common:confirmDeletionMessage",
                "Are you sure you want to delete this item? This action cannot be undone.",
              )}
          </Typography>
          {warning && <Alert severity={warningSeverity}>{warning}</Alert>}

          {/* Footer */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
              gap: 1.5,
              mt: 1,
              flexWrap: "wrap",
            }}
          >
            <Button
              key="cancel"
              onClick={onClose}
              disabled={deleting}
              autoFocus
              sx={[actionSx, { color: "text.secondary" }]}
            >
              {t("common:cancel")}
            </Button>
            {onSecondary && (
              <Button
                key="secondary"
                onClick={onSecondary}
                variant={secondaryVariant}
                disabled={deleting}
                // A promoted (contained) action carries its own emphasis, so
                // the subdued text colour only applies to a plain one.
                sx={[
                  actionSx,
                  secondaryVariant === "contained"
                    ? {}
                    : { color: "text.secondary" },
                ]}
              >
                {secondaryLabel ?? t("common:cancel")}
              </Button>
            )}
            <Button
              key="confirm"
              onClick={onConfirm}
              color="error"
              variant={confirmVariant}
              disabled={deleting}
              sx={actionSx}
            >
              {confirmLabel ?? t("common:delete")}
            </Button>
          </Box>
        </Box>
      </Box>
    </Modal>
  );
}
