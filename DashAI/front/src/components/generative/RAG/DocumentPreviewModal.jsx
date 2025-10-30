import { Dialog, DialogTitle, DialogContent, Box } from "@mui/material";
import PropTypes from "prop-types";

export default function DocumentPreviewModal({
  open,
  onClose,
  document,
  txtContent,
}) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Preview Document</DialogTitle>
      <DialogContent>
        {document && document.file_type === "pdf" && document.preview && (
          <iframe
            src={document.preview}
            title="PDF Preview"
            width="100%"
            height="600px"
            style={{ border: 0 }}
          />
        )}
        {document && document.file_type === "txt" && (
          <pre style={{ maxHeight: 600, overflow: "auto" }}>{txtContent}</pre>
        )}
        {document && !["pdf", "txt"].includes(document.file_type) && (
          <Box>No preview available for this file type.</Box>
        )}
      </DialogContent>
    </Dialog>
  );
}

DocumentPreviewModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  document: PropTypes.object,
  txtContent: PropTypes.string,
};
