import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useTranslation } from "react-i18next";

export default function DeleteConfirmationModal({
  open,
  onClose,
  onConfirm,
  content,
  onExited,
}) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const { t } = useTranslation(["common"]);

  return (
    <Dialog
      fullScreen={fullScreen}
      open={open}
      onClose={onClose}
      aria-labelledby="delete-confirmation-dialog-title"
      keepMounted={false}
      slotProps={{
        transition: { onExited },
      }}
    >
      <DialogTitle id="delete-confirmation-dialog-title">
        {t("common:confirmDeletion")}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {content ||
            t(
              "common:confirmDeletionMessage",
              "Are you sure you want to delete this item? This action cannot be undone.",
            )}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          {t("common:cancel")}
        </Button>
        <Button onClick={onConfirm} color="error" autoFocus>
          {t("common:delete")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
