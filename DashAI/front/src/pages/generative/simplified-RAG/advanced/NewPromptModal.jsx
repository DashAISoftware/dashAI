import React, { useState, useCallback, useEffect } from "react";
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
  TextField,
  Box,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { generateSequentialName } from "../../../../utils/nameGenerator";
import PlaceholdersList from "../../../../components/generative/RAG/PlaceholdersList";
import { getCustomPrompts, createRAGPrompt } from "../../../../api/rag";

export default function NewPromptModal({
  open,
  handleClose,
  onPromptCreated,
  existingPrompts = [],
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["generative"]);
  const [promptTypes, setPromptTypes] = useState([]);
  const selectedPromptType = "CustomRAGGenerationPrompt"; // Default to RAGGenerationPrompt
  const [promptName, setPromptName] = useState("");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [promptLanguage, setPromptLanguage] = useState("en");
  const [defaultPromptName, setDefaultPromptName] = useState("");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const allRequiredPresent = React.useMemo(() => {
    if (!selectedPromptType) return false;
    const selectedType = promptTypes.find(
      (type) => type.name === selectedPromptType,
    );
    if (!selectedType || !selectedType.metadata) return false;
    const required = selectedType.metadata.required_placeholders || [];
    return required.every((ph) => promptTemplate.includes(ph));
  }, [selectedPromptType, promptTypes, promptTemplate]);

  const canSave = Boolean(
    selectedPromptType && promptName.trim() && allRequiredPresent,
  );

  useEffect(() => {
    if (open) {
      getCustomPrompts()
        .then((data) => setPromptTypes(data))
        .catch(() => setPromptTypes([]));

      const generatedName = generateSequentialName({
        base: "Prompt",
        items: existingPrompts,
      });
      setDefaultPromptName(generatedName.defaultName);
      setPromptName(generatedName.defaultName);
      setPromptTemplate("");
      setPromptLanguage("en");
      setHasUnsavedChanges(false);
    }
  }, [open, existingPrompts]);

  const handlePromptNameChange = useCallback((e) => {
    setPromptName(e.target.value);
    setHasUnsavedChanges(true);
  }, []);

  const handlePromptTemplateChange = useCallback((e) => {
    setPromptTemplate(e.target.value);
    setHasUnsavedChanges(true);
  }, []);

  const handleConfirmClose = useCallback(() => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(
        t("generative:simplifiedRag.newPrompt.unsavedChanges")
      );
      if (!confirmed) return;
    }
    setHasUnsavedChanges(false);
    handleClose();
  }, [hasUnsavedChanges, handleClose, t]);

  const handleSave = useCallback(async () => {
    try {
      const result = await createRAGPrompt({
        class_name: selectedPromptType,
        name: promptName,
        parameters: {
          template: promptTemplate,
          ...(promptLanguage ? { language: promptLanguage } : {}),
        },
      });
      if (result && result.id) {
        enqueueSnackbar(t("generative:simplifiedRag.newPrompt.success"), { variant: "success" });
        setHasUnsavedChanges(false);
        await onPromptCreated(result.id);
      }
    } catch (error) {
      console.error("Error creating prompt:", error);
      enqueueSnackbar(t("generative:simplifiedRag.newPrompt.error"), { variant: "error" });
    }
  }, [promptName, promptTemplate, selectedPromptType, onPromptCreated, enqueueSnackbar, t]);

  return (
    <Dialog
      open={open}
      onClose={handleConfirmClose}
      fullWidth
      maxWidth="md"
      aria-labelledby="new-prompt-dialog-title"
      PaperProps={{ sx: { minHeight: 600, borderRadius: 2 } }}
    >
      <DialogTitle id="new-prompt-dialog-title">
        <Grid container alignItems="center" justifyContent="space-between">
          <Grid item>
            <Typography variant="h6" component="h2">
              {t("generative:simplifiedRag.newPrompt.title")}
            </Typography>
          </Grid>
          <Grid item>
            <IconButton edge="end" color="inherit" onClick={handleConfirmClose}>
              <CloseIcon />
            </IconButton>
          </Grid>
        </Grid>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            {t("generative:simplifiedRag.newPrompt.description")}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {t("generative:simplifiedRag.newPrompt.placeholdersInfo")}
          </Typography>
        </Box>

        <TextField
          fullWidth
          label={t("generative:simplifiedRag.newPrompt.nameLabel")}
          value={promptName}
          onChange={handlePromptNameChange}
          sx={{ mt: 2, mb: 2 }}
          required
          error={!promptName.trim()}
          helperText={!promptName.trim() ? t("generative:simplifiedRag.newPrompt.nameRequired") : ""}
          InputLabelProps={{ required: false }}
        />

        <TextField
          select
          fullWidth
          label={t("generative:simplifiedRag.newPrompt.languageLabel") || "Language (optional)"}
          value={promptLanguage}
          onChange={(e) => {
            setPromptLanguage(e.target.value);
            setHasUnsavedChanges(true);
          }}
          sx={{ mb: 2 }}
          SelectProps={{ native: true }}
        >
          <option value="">— No language —</option>
          <option value="en">English</option>
          <option value="es">Español</option>
          <option value="pt">Português</option>
        </TextField>

        {selectedPromptType &&
          (() => {
            const selectedType = promptTypes.find(
              (type) => type.name === selectedPromptType,
            );
            if (!selectedType || !selectedType.metadata) return null;
            return (
              <PlaceholdersList
                required={selectedType.metadata.required_placeholders || []}
                descriptions={
                  selectedType.metadata.placeholder_descriptions || {}
                }
                template={promptTemplate}
              />
            );
          })()}

        <TextField
          fullWidth
          label={t("generative:simplifiedRag.newPrompt.promptLabel")}
          placeholder={t("generative:simplifiedRag.newPrompt.promptPlaceholder")}
          multiline
          minRows={6}
          value={promptTemplate}
          onChange={handlePromptTemplateChange}
          sx={{ mt: 2 }}
          InputLabelProps={{ shrink: true }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleConfirmClose}>{t("generative:simplifiedRag.newPrompt.cancel")}</Button>
        <Button
          variant="contained"
          disabled={!canSave}
          onClick={handleSave}
        >
          {t("generative:simplifiedRag.newPrompt.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

