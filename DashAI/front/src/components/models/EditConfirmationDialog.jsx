import React from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Button,
  Alert,
  AlertTitle,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import {
  Warning as WarningIcon,
  DeleteSweep as DeleteSweepIcon,
  RestartAlt as RestartAltIcon,
} from "@mui/icons-material";

/**
 * Confirmation dialog for editing run parameters
 * Warns user about consequences of overwriting existing model
 */
function EditConfirmationDialog({
  open,
  onClose,
  onConfirm,
  run,
  hasOperations = false,
}) {
  if (!run) {
    return null;
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Confirm Parameter Update</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          You are about to update the parameters for run{" "}
          <strong>{run.name}</strong>. This action will have the following
          consequences:
        </DialogContentText>

        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>Important</AlertTitle>
          The following data will be permanently deleted:
        </Alert>

        <List dense>
          <ListItem>
            <ListItemIcon>
              <DeleteSweepIcon color="warning" />
            </ListItemIcon>
            <ListItemText
              primary="All existing metrics will be cleared"
              secondary="Training, validation, and test metrics"
            />
          </ListItem>
          <ListItem>
            <ListItemIcon>
              <DeleteSweepIcon color="warning" />
            </ListItemIcon>
            <ListItemText
              primary="Training results will be reset"
              secondary="Start time, end time, and delivery time"
            />
          </ListItem>
          {hasOperations && (
            <ListItem>
              <ListItemIcon>
                <WarningIcon color="error" />
              </ListItemIcon>
              <ListItemText
                primary="Existing explainers and predictions may become invalid"
                secondary="You may need to recreate them after retraining"
              />
            </ListItem>
          )}
        </List>

        <Box sx={{ mt: 2, p: 2, bgcolor: "info.light", borderRadius: 1 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <RestartAltIcon color="info" />
            <DialogContentText sx={{ color: "info.contrastText", mb: 0 }}>
              The run will be automatically retrained after updating parameters.
            </DialogContentText>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} variant="outlined">
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color="warning"
          autoFocus
        >
          Update & Retrain
        </Button>
      </DialogActions>
    </Dialog>
  );
}

EditConfirmationDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
  }),
  hasOperations: PropTypes.bool,
};

export default EditConfirmationDialog;
