import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";

/**
 * Confirms closing the upload dialog while its files are still being processed.
 *
 * The files already sent keep running in Data, so the choice is only whether to
 * stay on the progress panel or leave it.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the confirmation is visible.
 * @param {Function} props.onCancel - Stays on the progress panel.
 * @param {Function} props.onConfirm - Stops waiting and closes the dialog.
 * @returns {JSX.Element}
 */
export default function CloseUploadConfirmDialog({
  open,
  onCancel,
  onConfirm,
}) {
  const { t } = useTranslation(["generative", "common"]);

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>
        {t("generative:documentUpload.closeConfirmTitle")}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {t("generative:documentUpload.closeConfirmBody")}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>{t("common:cancel")}</Button>
        <Button variant="contained" color="warning" onClick={onConfirm}>
          {t("generative:documentUpload.closeConfirmAction")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

CloseUploadConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onCancel: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
};
