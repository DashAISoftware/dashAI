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
import { generateSequentialName } from "../../../utils/nameGenerator";
import PlaceholdersList from "./PlaceholdersList";

import { getCustomPrompts, createRAGPrompt } from "../../../api/rag";

export default function NewPromptModal({
  open,
  handleClose,
  onPromptCreated,
  existingPrompts = [],
}) {
  const [promptTypes, setPromptTypes] = React.useState([]);
  /* const [selectedPromptType, setSelectedPromptType] = React.useState(""); */
  const selectedPromptType = "CustomGenerationPrompt"; // Default to GenerationPrompt
  const [promptName, setPromptName] = React.useState("");
  const [promptTemplate, setPromptTemplate] = React.useState("");
  const [defaultPromptName, setDefaultPromptName] = React.useState("");

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

  React.useEffect(() => {
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
      /* setSelectedPromptType(""); */
      setPromptTemplate("");
    }
  }, [open]);

  const handlePromptTypeChange = (event) => {
    const typeName = event.target.value;
    /* setSelectedPromptType(typeName); */
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
              Create a new Prompt
            </Typography>
          </Grid>
          <Grid item>
            <IconButton edge="end" color="inherit" onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          </Grid>
        </Grid>
      </DialogTitle>
      <Typography variant="body2" sx={{ px: 3 }}>
        Prompt template defines how the chunks (pieces of documents) and chat messages are integrated to generate responses. Customize the prompt to tailor the behavior of your RAG sessions.
        Use `{`chunks`}` to represent where the retrieved document chunks will be inserted, and `{`input`}` for the user query.
      </Typography>
      <DialogContent dividers>
        <TextField
          fullWidth
          label="Prompt Name"
          value={promptName}
          onChange={(e) => setPromptName(e.target.value)}
          sx={{ mt: 2 }}
          required
          error={!promptName.trim()}
          helperText={!promptName.trim() ? "Prompt name is required" : ""}
          InputLabelProps={{ required: false }}
        />

        {/* <FormControl fullWidth sx={{ mt: 2 }}>
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
        </FormControl> */}
        {selectedPromptType &&
          (() => {
            const selectedType = promptTypes.find(
              (type) => type.name === selectedPromptType,
            );
            if (!selectedType || !selectedType.metadata) return null;
            return (
              <PlaceholdersList
                required={selectedType.metadata.required_placeholders || []}
                /* optional={selectedType.metadata.optional_placeholders || []} */
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
          minRows={4}
          value={promptTemplate}
          onChange={(e) => setPromptTemplate(e.target.value)}
          sx={{ mt: 2 }}
          InputLabelProps={{ shrink: true }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={!canSave}
          onClick={async () => {
            const result = await createRAGPrompt({
              class_name: selectedPromptType,
              name: promptName,
              parameters: {
                template: promptTemplate,
              },
            });
            if (onPromptCreated && result && result.id) {
              await onPromptCreated(result.id);
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
