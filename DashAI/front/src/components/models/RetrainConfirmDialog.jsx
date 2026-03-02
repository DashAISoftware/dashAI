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
import { Trans, useTranslation } from "react-i18next";

/**
 * RetrainConfirmDialog - Confirms re-training a run with existing operations
 */
export default function RetrainConfirmDialog({
  open,
  onClose,
  onConfirm,
  run,
  operationsCount,
  mode = "retrain",
}) {
  const { t } = useTranslation(["models", "common"]);

  const hasOperations =
    operationsCount &&
    (operationsCount.explainers > 0 || operationsCount.predictions > 0);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {hasOperations && <WarningIcon color="warning" />}
          <Typography variant="h6">
            {mode === "save"
              ? t("models:label.saveParameterChanges")
              : t("models:label.retrainModel")}
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {hasOperations ? (
          <>
            <Alert severity="warning" sx={{ mb: 2 }}>
              {mode === "save"
                ? t("models:message.saveWillDeleteOperations")
                : t("models:label.retrainWillDeleteOperations")}
            </Alert>
            <DialogContentText>
              {mode === "save" ? (
                <Trans i18nKey="models:label.saveWillDeleteOperationsDetails">
                  Saving "<strong>{{ runName: run?.name }}</strong>" will reset
                  the run. The following will be deleted when you train again:
                </Trans>
              ) : (
                <Trans i18nKey="models:label.retrainWillDeleteOperationsDetails">
                  Re-training run "<strong>{{ runName: run?.name }}</strong>"
                  will delete:
                </Trans>
              )}
            </DialogContentText>
            <Box sx={{ mt: 2, pl: 2 }}>
              {operationsCount.explainers > 0 && (
                <Typography variant="body2">
                  <Trans
                    i18nKey="models:label.explainersCount"
                    count={operationsCount.explainers}
                  >
                    • <strong>{{ count: operationsCount.explainers }}</strong>{" "}
                    explainer
                  </Trans>
                </Typography>
              )}
              {operationsCount.predictions > 0 && (
                <Typography variant="body2">
                  <Trans
                    i18nKey="models:label.predictionsCount"
                    count={operationsCount.predictions}
                  >
                    • <strong>{{ count: operationsCount.predictions }}</strong>{" "}
                    prediction
                  </Trans>
                </Typography>
              )}
            </Box>
            <DialogContentText sx={{ mt: 2 }}>
              {t("models:label.operationsWillBeDeletedWarning")}
            </DialogContentText>
          </>
        ) : (
          <DialogContentText>
            <Trans i18nKey="models:label.retrainConfirmDetails">
              Are you sure you want to re-train run "
              <strong>{{ runName: run?.name }}</strong>
              "?
            </Trans>
          </DialogContentText>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>{t("common:cancel")}</Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color={hasOperations ? "warning" : "primary"}
          autoFocus
        >
          {mode === "save"
            ? t("common:saveChanges")
            : hasOperations
              ? t("models:button.deleteAndRetrain")
              : t("models:button.retrain")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

RetrainConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  mode: PropTypes.oneOf(["retrain", "save"]),
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
  }),
  operationsCount: PropTypes.shape({
    explainers: PropTypes.number,
    predictions: PropTypes.number,
  }),
};
