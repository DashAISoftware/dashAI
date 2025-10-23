import React from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Typography,
} from "@mui/material";

export default function TemplateModal({ open, handleClose, template }) {
  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Prompt</DialogTitle>
      <DialogContent>
        <DialogContentText>
          <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
            {template}
          </Typography>
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} autoFocus>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}

TemplateModal.propTypes = {
  open: PropTypes.bool.isRequired,
  handleClose: PropTypes.func.isRequired,
  template: PropTypes.string,
};
