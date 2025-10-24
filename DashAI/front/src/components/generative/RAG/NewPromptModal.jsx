import React from "react";
import CloseIcon from "@mui/icons-material/Close";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Grid,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";

import TextField from "@mui/material/TextField";

import { getPromptChildren, createRAGPrompt } from "../../../api/rag";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import Tooltip from "@mui/material/Tooltip";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";

export default function NewPromptModal({ open, handleClose, onPromptCreated }) {
  const [promptTypes, setPromptTypes] = React.useState([]);
  const [selectedPromptType, setSelectedPromptType] = React.useState("");
  const [promptName, setPromptName] = React.useState("");
  const [promptTemplate, setPromptTemplate] = React.useState("");

  React.useEffect(() => {
    if (open) {
      getPromptChildren()
        .then((data) => setPromptTypes(data))
        .catch(() => setPromptTypes([]));
    }
  }, [open]);

  const handlePromptTypeChange = (event) => {
    const typeName = event.target.value;
    setSelectedPromptType(typeName);
    const selectedType = promptTypes.find((type) => type.name === typeName);
    if (
      selectedType &&
      selectedType.metadata &&
      selectedType.metadata.template
    ) {
      setPromptTemplate(selectedType.metadata.template);
    } else {
      setPromptTemplate("");
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      maxWidth="md"
      aria-labelledby="new-prompt-dialog-title"
      PaperProps={{ sx: { minHeight: 600, borderRadius: 2 } }}
    >
      <DialogTitle id="new-prompt-dialog-title">
        <Grid container alignItems="center" justifyContent="space-between">
          <Grid item>
            <Typography variant="h6" component="h2">
              Create New Prompt
            </Typography>
          </Grid>
          <Grid item>
            <IconButton edge="end" color="inherit" onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          </Grid>
        </Grid>
      </DialogTitle>
      <DialogContent dividers>
        <TextField
          fullWidth
          label="Prompt Name"
          value={promptName}
          onChange={(e) => setPromptName(e.target.value)}
          sx={{ mt: 2 }}
        />

        <FormControl fullWidth sx={{ mt: 2 }}>
          <InputLabel id="prompt-type-label">Prompt Type</InputLabel>
          <Select
            labelId="prompt-type-label"
            id="prompt-type-select"
            value={selectedPromptType}
            label="Prompt Type"
            onChange={handlePromptTypeChange}
          >
            {promptTypes.map((type) => (
              <MenuItem key={type.name} value={type.name}>
                {type.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        {/* Mostrar placeholders si hay un tipo seleccionado, en listas verticales */}
        {selectedPromptType &&
          (() => {
            const selectedType = promptTypes.find(
              (type) => type.name === selectedPromptType,
            );
            if (!selectedType || !selectedType.metadata) return null;
            const required = selectedType.metadata.required_placeholders || [];
            const optional = selectedType.metadata.optional_placeholders || [];
            return (
              <div style={{ marginTop: 16, marginBottom: 16 }}>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 64 }}>
                  <div>
                    <Typography variant="subtitle1" gutterBottom>
                      Required Placeholders
                    </Typography>
                    <ul style={{ marginTop: 0 }}>
                      {required.map((ph) => {
                        const isPresent = promptTemplate.includes(ph);
                        return (
                          <li
                            key={ph}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            {isPresent ? (
                              <CheckCircleIcon
                                fontSize="small"
                                color="success"
                              />
                            ) : (
                              <WarningAmberIcon
                                fontSize="small"
                                color="warning"
                              />
                            )}
                            <strong>{ph}</strong>
                            <Tooltip
                              title={
                                selectedType.metadata
                                  .placeholder_descriptions?.[ph] || ""
                              }
                              placement="right"
                            >
                              <HelpOutlineIcon
                                fontSize="small"
                                color="action"
                                style={{ cursor: "pointer" }}
                              />
                            </Tooltip>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                  <div>
                    <Typography variant="subtitle1" gutterBottom>
                      Optional Placeholders
                    </Typography>
                    <ul style={{ marginTop: 0 }}>
                      {optional.map((ph) => {
                        const isPresent = promptTemplate.includes(ph);
                        return (
                          <li
                            key={ph}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            {isPresent && (
                              <CheckCircleIcon
                                fontSize="small"
                                color="success"
                              />
                            )}
                            <strong>{ph}</strong>
                            <Tooltip
                              title={
                                selectedType.metadata
                                  .placeholder_descriptions?.[ph] || ""
                              }
                              placement="right"
                            >
                              <HelpOutlineIcon
                                fontSize="small"
                                color="action"
                                style={{ cursor: "pointer" }}
                              />
                            </Tooltip>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })()}

        <TextField
          fullWidth
          label="Prompt"
          multiline
          minRows={4}
          value={promptTemplate}
          onChange={(e) => setPromptTemplate(e.target.value)}
          sx={{ mt: 2 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={async () => {
            await createRAGPrompt({
              class_name: selectedPromptType,
              name: promptName,
              parameters: {
                template: promptTemplate,
                /* name: promptName */
              },
            });
            if (onPromptCreated) {
              await onPromptCreated();
            } else {
              handleClose();
            }
          }}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}
