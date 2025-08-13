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
  List,
  ListItem,
  ListItemText,
  Chip,
  IconButton,
} from "@mui/material";
import { Close, Transform } from "@mui/icons-material";

export function SaveDatasetModal({
  open,
  onClose,
  onSaveDataset,
  appliedConverters,
}) {
  const [name, setName] = useState("");
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const handleSubmit = () => {
    if (name.trim()) {
      onSaveDataset(name.trim());
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Save Processed Dataset
        <IconButton
          onClick={onClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3, mt: 1 }}>
          <TextField
            fullWidth
            label="Dataset Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            variant="outlined"
          />

          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Applied Transformations:
            </Typography>
            {appliedConverters.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No transformations applied.
              </Typography>
            ) : (
              <List dense>
                {appliedConverters.map((converter) => {
                  const scope = converter.parameters?.scope;
                  const scopeText = scope
                    ? `Columns: ${
                        scope.columns?.length ? scope.columns.join(", ") : "All"
                      } | Rows: ${
                        scope.rows?.length ? scope.rows.join(", ") : "All"
                      }`
                    : "";

                  return (
                    <ListItem
                      key={converter.id}
                      sx={{
                        px: 0,
                        flexDirection: "column",
                        alignItems: "flex-start",
                      }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          width: "100%",
                        }}
                      >
                        <Transform
                          sx={{ mr: 1, color: "#00BEBB", fontSize: 20 }}
                        />
                        <ListItemText
                          primary={converter.converter}
                          secondary={scopeText}
                        />
                        <Chip
                          label={formatDate(converter.created)}
                          size="small"
                        />
                      </Box>
                    </ListItem>
                  );
                })}
              </List>
            )}
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={!name.trim()}
        >
          Save Dataset
        </Button>
      </DialogActions>
    </Dialog>
  );
}
