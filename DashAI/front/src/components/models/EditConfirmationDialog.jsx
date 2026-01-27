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
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation(["models", "common"]);

  if (!run) {
    return null;
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t("models:label.confirmParameterUpdate")}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          {t("models:message.aboutToUpdateParameters", { runName: run.name })}
        </DialogContentText>

        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>{t("common:important")}</AlertTitle>
          {t("models:message.dataWillBeDeleted")}
        </Alert>

        <List dense>
          <ListItem>
            <ListItemIcon>
              <DeleteSweepIcon color="warning" />
            </ListItemIcon>
            <ListItemText
              primary={t("models:message.metricsWillBeCleared")}
              secondary={t("models:message.trainValidationTestMetrics")}
            />
          </ListItem>
          <ListItem>
            <ListItemIcon>
              <DeleteSweepIcon color="warning" />
            </ListItemIcon>
            <ListItemText
              primary={t("models:message.trainingResultsWillBeReset")}
              secondary={t("models:message.startEndDeliveryTime")}
            />
          </ListItem>
          {hasOperations && (
            <ListItem>
              <ListItemIcon>
                <WarningIcon color="error" />
              </ListItemIcon>
              <ListItemText
                primary={t("models:message.operationsMayBecomeInvalid")}
                secondary={t("models:message.mayNeedToRecreate")}
              />
            </ListItem>
          )}
        </List>

        <Box sx={{ mt: 2, p: 2, bgcolor: "info.light", borderRadius: 1 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <RestartAltIcon color="info" />
            <DialogContentText sx={{ color: "info.contrastText", mb: 0 }}>
              {t("models:message.willBeRetrainedAfterUpdate")}
            </DialogContentText>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} variant="outlined">
          {t("common:cancel")}
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color="warning"
          autoFocus
        >
          {t("models:button.updateAndRetrain")}
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
