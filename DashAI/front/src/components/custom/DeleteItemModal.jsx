import React from "react";
import PropTypes from "prop-types";
import { GridActionsCellItem } from "@mui/x-data-grid";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Tooltip,
  Typography,
} from "@mui/material";

/**
 * Modal to confirm deletion of an item from the table
 * @param {Object} props
 * @param {Function} props.deleteFromTable - Function to delete the item from the table
 */
function DeleteItemModal({ deleteFromTable }) {
  const [open, setOpen] = React.useState(false);
  const handleDelete = () => {
    deleteFromTable();
    setOpen(false);
  };
  return (
    <React.Fragment>
      {/* Delete icon button */}
      <Tooltip
        title={<Typography>Delete item</Typography>}
        placement="top"
        arrow
      >
        <GridActionsCellItem
          key="delete-button"
          icon={<DeleteIcon />}
          label="Delete"
          onClick={() => setOpen(true)}
          sx={{ color: "error.main" }}
        />
      </Tooltip>
      {/* Modal to confirm deletion */}
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Confirm Deletion</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this item?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} autoFocus>
            Cancel
          </Button>
          <Button onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}
DeleteItemModal.propTypes = {
  deleteFromTable: PropTypes.func.isRequired,
};

export default DeleteItemModal;
