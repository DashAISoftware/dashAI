import { Dialog, DialogTitle, DialogContent, Box } from "@mui/material";
import { createPortal } from "react-dom";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { normalizeUrl } from "../../../utils/urlUtils";

export default function DocumentPreviewModal({
  open,
  onClose,
  document,
  txtContent,
}) {
  const { t } = useTranslation(["generative"]);
  const fileType = document?.file_type || document?.type;
  const preview = normalizeUrl(document?.preview);

  const dialogContent = (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{t("generative:rag.documentPreview.title")}</DialogTitle>
      <DialogContent>
        {document && fileType === "pdf" && preview && (
          <iframe
            src={preview}
            title={t("generative:rag.documentPreview.pdfPreview")}
            width="100%"
            height="600px"
            style={{ border: 0 }}
          />
        )}
        {document && fileType === "txt" && (
          <pre style={{ maxHeight: 600, overflow: "auto" }}>{txtContent}</pre>
        )}
        {document && !["pdf", "txt"].includes(fileType) && (
          <Box>{t("generative:rag.documentPreview.noPreview")}</Box>
        )}
      </DialogContent>
    </Dialog>
  );

  return createPortal(dialogContent, globalThis.document.body);
}

DocumentPreviewModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  document: PropTypes.object,
  txtContent: PropTypes.string,
};
