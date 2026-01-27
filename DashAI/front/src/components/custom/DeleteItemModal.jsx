import React from "react";
import PropTypes from "prop-types";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import TooltipedCellItem from "../shared/TooltipedCellItem";
import { useTranslation } from "react-i18next";

/**
 * Modal to confirm deletion of an item from the table
 * @param {Object} props
 * @param {Function} props.deleteFromTable - Function to delete the item from the table
 */
function DeleteItemModal({ deleteFromTable }) {
  const { t } = useTranslation("common");

  const [open, setOpen] = React.useState(false);
  const handleDelete = () => {
    deleteFromTable();
    setOpen(false);
  };
  return (
    <React.Fragment>
      <TooltipedCellItem
        key="delete-button"
        icon={<DeleteIcon />}
        label={t("common:delete")}
        tooltip="Delete item"
        onClick={() => setOpen(true)}
        sx={{ color: "error.main" }}
      />
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>{t("common:confirmDeletion")}</DialogTitle>
        <DialogContent>
          <DialogContentText>{t("common:areYouSureDelete")}</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} autoFocus>
            {t("common:cancel")}
          </Button>
          <Button onClick={handleDelete}>{t("common:delete")}</Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}
DeleteItemModal.propTypes = {
  deleteFromTable: PropTypes.func.isRequired,
};

export default DeleteItemModal;
