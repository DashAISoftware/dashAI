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
import { Close } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import ConverterHistoryList from "../converter/ConverterHistoryList";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import NoteBox from "../NoteBox";
import { generateSequentialName } from "../../../utils/nameGenerator";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

const EMPTY_ARRAY = [];

export function SaveDatasetModal({
  open,
  onClose,
  onSaveDataset,
  appliedConverters,
  existingDatasets = EMPTY_ARRAY,
}) {
  const [name, setName] = useState("");
  const [frozenDefaultName, setFrozenDefaultName] = useState("");
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

  const { defaultName } = useMemo(() => {
    if (tourContext && tourContext.run) {
      return { defaultName: "Clean_Personality_Dataset" };
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
        enqueueSnackbar(t("datasets:error.datasetExists"), {
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
      return t("common:nameRequired");
    }
    if (
      currentName !== frozenDefaultName &&
      existingDatasets.some((dataset) => dataset.name === currentName)
    ) {
      return t("datasets:error.datasetExists");
    }
    return null;
  };

  const nameError = getNameError();

  return (
    <Dialog open={open} onClose={() => {}} maxWidth="sm" fullWidth>
      <DialogTitle>
        {t("datasets:label.saveProcessedDataset")}
        <IconButton
          onClick={handleClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent data-tour="save-dataset-modal-notebook">
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3, mt: 1 }}>
          <NoteBox
            message={t("datasets:label.newDatasetCreatedWithTransformations")}
          />
          <TextField
            fullWidth
            label={t("datasets:label.datasetName")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            variant="outlined"
            error={Boolean(nameError)}
            helperText={nameError}
          />

          <Box>
            <Typography variant="subtitle2" gutterBottom>
              {t("datasets:label.appliedTransformations")}
            </Typography>
            {appliedConverters.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {t("datasets:label.noTransformationsApplied")}
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
              saveButtonText={t("datasets:button.saveDataset")}
              backButtonText={t("common:cancel")}
              dataTour="save-dataset-button-notebook"
            />
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
