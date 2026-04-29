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
  const [promptTypes, setPromptTypes] = useState([]);
  const selectedPromptType = "CustomGenerationPrompt"; // Default to GenerationPrompt
  const [promptName, setPromptName] = useState("");
  const [promptTemplate, setPromptTemplate] = useState("");
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
        "You have unsaved changes. Are you sure you want to cancel?"
      );
      if (!confirmed) return;
    }
    setHasUnsavedChanges(false);
    handleClose();
  }, [hasUnsavedChanges, handleClose]);

  const handleSave = useCallback(async () => {
    try {
      const result = await createRAGPrompt({
        class_name: selectedPromptType,
        name: promptName,
        parameters: {
          template: promptTemplate,
        },
      });
      if (result && result.id) {
        enqueueSnackbar("Prompt created successfully!", { variant: "success" });
        setHasUnsavedChanges(false);
        await onPromptCreated(result.id);
      }
    } catch (error) {
      console.error("Error creating prompt:", error);
      enqueueSnackbar("Failed to create prompt", { variant: "error" });
    }
  }, [promptName, promptTemplate, selectedPromptType, onPromptCreated, enqueueSnackbar]);

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
              Create a new Prompt
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
            Prompt template defines how the chunks (pieces of documents) and chat messages are integrated to generate responses. Customize the prompt to tailor the behavior of your RAG sessions.
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Use {`{chunks}`} to represent where the retrieved document chunks will be inserted, and {`{input}`} for the user message.
          </Typography>
        </Box>

        <TextField
          fullWidth
          label="Prompt Name"
          value={promptName}
          onChange={handlePromptNameChange}
          sx={{ mt: 2, mb: 2 }}
          required
          error={!promptName.trim()}
          helperText={!promptName.trim() ? "Prompt name is required" : ""}
          InputLabelProps={{ required: false }}
        />

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
          label="Prompt"
          placeholder={`Here you can modify the prompt, for example:\nEach user message is added as {input}\nThe sources are added as {chunks}`}
          multiline
          minRows={6}
          value={promptTemplate}
          onChange={handlePromptTemplateChange}
          sx={{ mt: 2 }}
          InputLabelProps={{ shrink: true }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleConfirmClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={!canSave}
          onClick={handleSave}
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}
