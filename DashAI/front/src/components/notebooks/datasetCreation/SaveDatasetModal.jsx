import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  Box,
  Typography,
  IconButton,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import ConverterHistoryList from "../converter/ConverterHistoryList";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import NoteBox from "../NoteBox";

export function SaveDatasetModal({
  open,
  onClose,
  onSaveDataset,
  appliedConverters,
}) {
  const [name, setName] = useState("");

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
          <NoteBox message="A new dataset will be created with these transformations. It can be used with other modules without affecting the original." />
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
              <ConverterHistoryList converters={appliedConverters} />
            )}
          </Box>

          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
            <FormSchemaButtonGroup
              onCancel={onClose}
              onFormSubmit={handleSubmit}
              formik={{
                errors: name.trim() ? {} : { name: "Name is required" },
              }}
              saveButtonText="Save Dataset"
              backButtonText="Cancel"
            />
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
