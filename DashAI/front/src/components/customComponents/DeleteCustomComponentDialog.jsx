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

function DeleteCustomComponentDialog({ component, onClose, onConfirm }) {
  const { t } = useTranslation(["customComponents", "common"]);
  const open = Boolean(component);

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{t("deleteDialog.title")}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          {t("deleteDialog.body", { name: component?.class_name })}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:cancel")}</Button>
        <Button color="error" variant="contained" onClick={onConfirm}>
          {t("actions.delete")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default DeleteCustomComponentDialog;
