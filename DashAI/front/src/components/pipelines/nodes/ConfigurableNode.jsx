import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  TextField,
  MenuItem,
} from "@mui/material";

function ConfigurableNode({
  open,
  onClose,
  onSave,
  savedConfig = {},
  configSchema,
  displayMode = "dialog",
}) {
  const [formValues, setFormValues] = useState({});

  useEffect(() => {
    if (Object.keys(formValues).length === 0) {
      const defaults = {};
      for (const field of configSchema?.fields || []) {
        defaults[field.name] = savedConfig[field.name] ?? field.default ?? "";
      }
      setFormValues(defaults);
    }
  }, [configSchema, savedConfig]);

  const handleChange = (fieldName) => (event) => {
    setFormValues((prev) => ({
      ...prev,
      [fieldName]: event.target.value,
    }));
  };

  const handleSubmit = () => {
    onSave(formValues);
    onClose();
  };

  const fields = (configSchema?.fields || []).map((field) => (
    <Box key={field.name} sx={{ my: 2 }}>
      {field.type === "select" ? (
        <TextField
          select
          fullWidth
          label={field.label || field.name}
          value={formValues[field.name] ?? ""}
          onChange={handleChange(field.name)}
        >
          {field.options.map((opt) => (
            <MenuItem key={opt} value={opt}>
              {opt}
            </MenuItem>
          ))}
        </TextField>
      ) : (
        <TextField
          fullWidth
          type={field.type === "number" ? "number" : "text"}
          label={field.label || field.name}
          value={formValues[field.name] ?? ""}
          onChange={handleChange(field.name)}
        />
      )}
    </Box>
  ));

  if (displayMode === "panel") {
    if (!open) return null;

    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {fields}
        <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="contained" onClick={handleSubmit}>
            Save
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Configure Node</DialogTitle>
      <DialogContent dividers>
        {fields}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default ConfigurableNode;
