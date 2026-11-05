import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";

/**
 * Confirms a large selection before it starts.
 *
 * Not a block: the upload still runs, the user is only told that hundreds of
 * files are processed one at a time and may take a while.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the confirmation is visible.
 * @param {number}   props.count - How many files would be uploaded.
 * @param {Function} props.onCancel - Keeps the dialog open for editing.
 * @param {Function} props.onConfirm - Proceeds with the upload.
 * @returns {JSX.Element}
 */
export default function LargeSelectionDialog({
  open,
  count,
  onCancel,
  onConfirm,
}) {
  const { t } = useTranslation(["generative", "common"]);

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>
        {t("generative:documentUpload.largeSelectionTitle")}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary">
          {t("generative:documentUpload.largeSelectionBody", { count })}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>{t("common:cancel")}</Button>
        <Button variant="contained" onClick={onConfirm}>
          {t("generative:documentUpload.largeSelectionConfirm")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

LargeSelectionDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  count: PropTypes.number.isRequired,
  onCancel: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
};
