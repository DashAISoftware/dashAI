import { useState, useEffect, useMemo } from "react";
import { Modal, TextField, Box, Typography, IconButton } from "@mui/material";
import { Close } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import ConverterHistoryList from "../converter/ConverterHistoryList";
import StepperNavigationFooter from "../../shared/StepperNavigationFooter";
import NoteBox from "../NoteBox";
import { generateSequentialName } from "../../../utils/nameGenerator";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

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
    <Modal open={open} onClose={() => {}}>
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: { xs: "90%", sm: 560 },
          bgcolor: "background.paper",
          borderRadius: 2,
          boxShadow: 12,
          p: 0,
          outline: "none",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <Typography variant="h6" component="h2">
            {t("datasets:label.saveProcessedDataset")}
          </Typography>
          <IconButton
            onClick={handleClose}
            size="small"
            sx={{ color: "text.secondary" }}
          >
            <Close />
          </IconButton>
        </Box>

        {/* Content */}
        <Box
          sx={{ p: 3, display: "flex", flexDirection: "column", gap: 3 }}
          data-tour="save-dataset-modal-notebook"
        >
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

          <StepperNavigationFooter
            onBack={handleClose}
            onNext={handleSubmit}
            nextDisabled={Boolean(nameError)}
            backLabel={t("common:cancel")}
            nextLabel={t("datasets:button.saveDataset")}
            variant="save"
          />
        </Box>
      </Box>
    </Modal>
  );
}
