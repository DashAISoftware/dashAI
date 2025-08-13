import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  IconButton,
} from "@mui/material";
import { Close } from "@mui/icons-material";

export function CreateNotebookModal({ open, onClose, onCreateNotebook }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = () => {
    onCreateNotebook({
      name: name.trim() || "Untitled Notebook",
      description: description.trim() || "",
    });
    handleClose();
  };

  const handleClose = () => {
    setName("");
    setDescription("");
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Create a New Notebook
        <IconButton
          onClick={handleClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          <Typography
            variant="h6"
            sx={{
              whiteSpace: "normal",
              wordBreak: "break-word",
              my: 2,
            }}
          >
            Name your Notebook
          </Typography>

          {/* Notebook name */}
          <TextField
            fullWidth
            label="Notebook Name"
            name="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            variant="outlined"
            placeholder="Enter a name for your notebook (optional)"
            sx={{ mb: 2 }}
          />

          {/* Notebook description */}
          <TextField
            fullWidth
            label="Notebook Description"
            name="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            variant="outlined"
            multiline
            rows={3}
            placeholder="Describe what this notebook will be used for (optional)"
            sx={{ mb: 2 }}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          sx={{
            bgcolor: "#00BEBB",
            "&:hover": { bgcolor: "#008582" },
          }}
        >
          Create Notebook
        </Button>
      </DialogActions>
    </Dialog>
  );
}
