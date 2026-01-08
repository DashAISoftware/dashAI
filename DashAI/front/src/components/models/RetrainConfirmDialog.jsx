import React from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Alert,
  Box,
  Typography,
} from "@mui/material";
import { Warning as WarningIcon } from "@mui/icons-material";

/**
 * RetrainConfirmDialog - Confirms re-training a run with existing operations
 */
export default function RetrainConfirmDialog({
  open,
  onClose,
  onConfirm,
  run,
  operationsCount,
}) {
  const hasOperations =
    operationsCount &&
    (operationsCount.explainers > 0 || operationsCount.predictions > 0);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {hasOperations && <WarningIcon color="warning" />}
          <Typography variant="h6">Re-train Model?</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {hasOperations ? (
          <>
            <Alert severity="warning" sx={{ mb: 2 }}>
              This run has existing operations that will be deleted
            </Alert>
            <DialogContentText>
              Re-training run "<strong>{run?.name}</strong>" will delete:
            </DialogContentText>
            <Box sx={{ mt: 2, pl: 2 }}>
              {operationsCount.explainers > 0 && (
                <Typography variant="body2">
                  • <strong>{operationsCount.explainers}</strong> explainer
                  {operationsCount.explainers !== 1 ? "s" : ""}
                </Typography>
              )}
              {operationsCount.predictions > 0 && (
                <Typography variant="body2">
                  • <strong>{operationsCount.predictions}</strong> prediction
                  {operationsCount.predictions !== 1 ? "s" : ""}
                </Typography>
              )}
            </Box>
            <DialogContentText sx={{ mt: 2 }}>
              These operations will be permanently removed and cannot be
              recovered. Are you sure you want to continue?
            </DialogContentText>
          </>
        ) : (
          <DialogContentText>
            Are you sure you want to re-train run "<strong>{run?.name}</strong>
            "?
          </DialogContentText>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color={hasOperations ? "warning" : "primary"}
          autoFocus
        >
          {hasOperations ? "Delete & Re-train" : "Re-train"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

RetrainConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
  }),
  operationsCount: PropTypes.shape({
    explainers: PropTypes.number,
    predictions: PropTypes.number,
  }),
};
