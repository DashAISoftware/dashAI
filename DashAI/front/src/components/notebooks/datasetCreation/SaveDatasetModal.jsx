import { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  Box,
  Typography,
  IconButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Close } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import ConverterHistoryList from "../converter/ConverterHistoryList";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import NoteBox from "../NoteBox";
import { generateSequentialName } from "../../../utils/nameGenerator";
import { useTourContext } from "../../tour/TourProvider";

export function SaveDatasetModal({
  open,
  onClose,
  onSaveDataset,
  appliedConverters,
  existingDatasets = [],
}) {
  const [name, setName] = useState("");
  const [frozenDefaultName, setFrozenDefaultName] = useState("");
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();

  const { defaultName } = useMemo(() => {
    if (tourContext && tourContext.run) {
      return { defaultName: "Clean Personality Dataset" };
    }
    return generateSequentialName({
      base: "Dataset",
      items: existingDatasets,
    });
  }, [existingDatasets, open]);

  useEffect(() => {
    if (open && defaultName) {
      setFrozenDefaultName(defaultName);
      setName(defaultName);
    }
  }, [open, defaultName]);

  const handleSubmit = () => {
    const datasetName = name.trim();

    if (datasetName) {
      if (existingDatasets.some((dataset) => dataset.name === datasetName)) {
        enqueueSnackbar("A dataset with this name already exists", {
          variant: "warning",
        });
        return;
      }

      onSaveDataset(datasetName);
      handleClose();
    }
  };

  const handleClose = () => {
    onClose();
  };

  const getNameError = () => {
    const currentName = name.trim();
    if (!currentName) {
      return "Name is required";
    }
    if (
      currentName !== frozenDefaultName &&
      existingDatasets.some((dataset) => dataset.name === currentName)
    ) {
      return "A dataset with this name already exists";
    }
    return null;
  };

  const nameError = getNameError();

  return (
    <Dialog open={open} onClose={() => {}} maxWidth="sm" fullWidth>
      <DialogTitle>
        Save Processed Dataset
        <IconButton
          onClick={handleClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent data-tour="save-dataset-modal-notebook">
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3, mt: 1 }}>
          <NoteBox message="A new dataset will be created with these transformations. It can be used with other modules without affecting the original." />
          <TextField
            fullWidth
            label="Dataset Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            variant="outlined"
            error={Boolean(nameError)}
            helperText={nameError}
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
              onCancel={handleClose}
              onFormSubmit={handleSubmit}
              formik={{
                errors: nameError ? { name: nameError } : {},
              }}
              saveButtonText="Save Dataset"
              backButtonText="Cancel"
              dataTour="save-dataset-button-notebook"
            />
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
