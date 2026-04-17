import React from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import { useTranslation } from "react-i18next";

function DeleteCustomComponentDialog({
  component,
  onClose,
  onConfirm,
  revert = false,
}) {
  const { t } = useTranslation(["customComponents", "common"]);
  const open = Boolean(component);
  const titleKey = revert ? "revertDialog.title" : "deleteDialog.title";
  const bodyKey = revert ? "revertDialog.body" : "deleteDialog.body";
  const confirmKey = revert ? "actions.revert" : "actions.delete";

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{t(titleKey)}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          {t(bodyKey, { name: component?.class_name })}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:cancel")}</Button>
        <Button
          color={revert ? "warning" : "error"}
          variant="contained"
          onClick={onConfirm}
        >
          {t(confirmKey)}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default DeleteCustomComponentDialog;
