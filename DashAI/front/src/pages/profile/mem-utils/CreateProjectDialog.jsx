import React, { useState } from "react";
import PropTypes from "prop-types";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";

import { useProjects } from "./ProjectContext";

const NAME_MAX_LENGTH = 150;

export default function CreateProjectDialog({ open, onClose }) {
  const { createProject } = useProjects();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const handleClose = () => {
    if (saving) return;
    setName("");
    setDescription("");
    setError("");
    onClose();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("El nombre es obligatorio.");
      return;
    }
    setSaving(true);
    try {
      // Selecting the new project remounts the app, which closes this dialog
      await createProject(name.trim(), description.trim() || undefined);
    } catch {
      setError("No se pudo crear el proyecto. Inténtalo nuevamente.");
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>Nuevo proyecto</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label="Nombre"
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setError("");
            }}
            error={Boolean(error)}
            helperText={error || " "}
            inputProps={{ maxLength: NAME_MAX_LENGTH }}
          />
          <TextField
            fullWidth
            multiline
            minRows={2}
            margin="dense"
            label="Descripción (opcional)"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" variant="contained" disabled={saving}>
            Crear
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

CreateProjectDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};
