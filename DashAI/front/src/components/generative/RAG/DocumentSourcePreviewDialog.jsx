import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import { getDocumentSourceViewAbsoluteUrl } from "../../../api/documents";

/**
 * Shows the original uploaded file (the PDF source) of a Data document.
 *
 * The parsed document has its own reader; this dialog is for the file the user
 * actually uploaded, so the upload progress list can open the PDF it just sent.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {Function} props.onClose - Called when the dialog asks to close.
 * @param {object}   props.document - The Data document whose source is shown.
 * @returns {JSX.Element}
 */
export default function DocumentSourcePreviewDialog({
  open,
  onClose,
  document,
}) {
  const { t } = useTranslation(["generative", "common"]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        {document?.name ?? t("generative:documentsBar.preview")}
      </DialogTitle>
      <DialogContent sx={{ p: 0, height: "75vh", overflow: "hidden" }}>
        {document && (
          <Box
            component="iframe"
            title={document.name}
            src={getDocumentSourceViewAbsoluteUrl(document.id)}
            sx={{ display: "block", width: "100%", height: "100%", border: 0 }}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:close")}</Button>
      </DialogActions>
    </Dialog>
  );
}

DocumentSourcePreviewDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  document: PropTypes.object,
};
