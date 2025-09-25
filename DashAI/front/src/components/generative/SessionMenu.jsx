import { useState } from "react";
import {
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  styled,
} from "@mui/material";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import DeleteIcon from "@mui/icons-material/Delete";
import InfoIcon from "@mui/icons-material/Info";
import DeleteSessionConfirmationModal from "./DeleteSessionConfirmationModal";

const DeleteMenuItem = styled(MenuItem)(({ theme }) => ({
  color: theme.palette.error.main,
  "& .MuiListItemIcon-root": {
    color: theme.palette.error.main,
  },
}));

export default function SessionMenu({ sessionId, onInfo, onDelete }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const open = Boolean(anchorEl);

  const handleClick = (event) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleAction = (action, id) => {
    if (action === onDelete) {
      // Open confirmation modal instead of deleting immediately
      setDeleteModalOpen(true);
    } else if (action) {
      action(id);
    }
    handleClose();
  };

  const handleDeleteConfirm = (id) => {
    if (onDelete) {
      onDelete(id);
    }
  };

  return (
    <>
      <IconButton
        aria-label="more options"
        aria-controls={open ? "session-menu" : undefined}
        aria-haspopup="true"
        aria-expanded={open ? "true" : undefined}
        onClick={handleClick}
        size="small"
        sx={{ color: "text.secondary" }}
      >
        <MoreHorizIcon fontSize="small" />
      </IconButton>
      <Menu
        id="session-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        onClick={(e) => e.stopPropagation()}
        slotProps={{
          list: {
            "aria-labelledby": "session-menu-button",
            dense: true,
          },
        }}
      >
        <MenuItem
          onClick={(e) => {
            e.stopPropagation();
            handleAction(onInfo, sessionId);
          }}
        >
          <ListItemIcon>
            <InfoIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Info</ListItemText>
        </MenuItem>
        <Divider />
        <DeleteMenuItem
          onClick={(e) => {
            e.stopPropagation();
            handleAction(onDelete, sessionId);
          }}
        >
          <ListItemIcon>
            <DeleteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </DeleteMenuItem>
      </Menu>
      {/* Confirmation Modal */}
      <DeleteSessionConfirmationModal
        open={deleteModalOpen}
        sessionId={sessionId}
        onClose={(e) => {
          e.stopPropagation();
          setDeleteModalOpen(false);
        }}
        onConfirm={(e) => {
          e.stopPropagation();
          handleDeleteConfirm(sessionId);
          setDeleteModalOpen(false);
        }}
      />
    </>
  );
}
