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

export default function DeleteSessionConfirmationModal({
  open,
  sessionId,
  onClose,
  onConfirm,
}) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const { t } = useTranslation(["common", "generative"]);

  return (
    <Dialog
      fullScreen={fullScreen}
      open={open}
      onClose={onClose}
      aria-labelledby="delete-confirmation-dialog-title"
    >
      <DialogTitle id="delete-confirmation-dialog-title">
        {t("common:confirmDeletion")}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {t("generative:label.deleteSessionConfirmation")}
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
