import { Dialog, DialogTitle, DialogContent, Box } from "@mui/material";
import { createPortal } from "react-dom";
import PropTypes from "prop-types";

export default function DocumentPreviewModal({
  open,
  onClose,
  document,
  txtContent,
}) {
  const fileType = document?.file_type || document?.type;
  const preview = document?.preview;

  const dialogContent = (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Preview Document</DialogTitle>
      <DialogContent>
        {document && fileType === "pdf" && preview && (
          <iframe
            src={preview}
            title="PDF Preview"
            width="100%"
            height="600px"
            style={{ border: 0 }}
          />
        )}
        {document && fileType === "txt" && (
          <pre style={{ maxHeight: 600, overflow: "auto" }}>{txtContent}</pre>
        )}
        {document && !["pdf", "txt"].includes(fileType) && (
          <Box>No preview available for this file type.</Box>
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
