import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
} from "@mui/material";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getRAGPrompts } from "../../../../api/rag";
import PromptAdvancedModal from "../advanced/PromptAdvancedModal";
import NewPromptModal from "../advanced/NewPromptModal";
import { getDescription, renderTemplateWithHighlights } from "./sectionUtils";

export default function PromptBody({
  promptId,
  setPromptId,
  onTokenCountChange,
}) {
  const { t, i18n } = useTranslation(["generative"]);
  const [prompts, setPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newPromptModalOpen, setNewPromptModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadPrompts = useCallback(async () => {
    try {
      const data = await getRAGPrompts();
      setPrompts(data || []);
    } catch (error) {
      console.error("Error loading RAG prompts:", error);
    }
  }, []);

  useEffect(() => {
    const loadPromptsWithLoader = async () => {
      await loadPrompts();
      setLoading(false);
    };
    loadPromptsWithLoader();
  }, [loadPrompts]);

  useEffect(() => {
    if (!prompts.length) return;

    if (promptId) {
      const found = prompts.find((p) => p.id === promptId);
      setSelectedPrompt(found || null);
      return;
    }

    if (!selectedPrompt) {
      setSelectedPrompt(prompts[0]);
      setPromptId(prompts[0].id);
    }
  }, [prompts, promptId, selectedPrompt, setPromptId]);

  useEffect(() => {
    if (selectedPrompt && onTokenCountChange) {
      const template = selectedPrompt.parameters?.template || "";
      const tokenCount = Math.ceil(template.length / 4);
      onTokenCountChange(tokenCount);
    } else if (!selectedPrompt && onTokenCountChange) {
      onTokenCountChange(0);
    }
  }, [selectedPrompt, onTokenCountChange]);

  const handlePromptChange = (event, newValue) => {
    setSelectedPrompt(newValue);
    if (newValue) {
      setPromptId(newValue.id);
      const template = newValue.parameters?.template || "";
      const tokenCount = Math.ceil(template.length / 4);
      onTokenCountChange?.(tokenCount);
    } else {
      setPromptId(null);
      onTokenCountChange?.(0);
    }
  };

  const handlePromptCreated = useCallback(async (newPromptId) => {
    const updatedPrompts = await getRAGPrompts();
    setPrompts(updatedPrompts || []);

    const newPrompt = (updatedPrompts || []).find((p) => p.id === newPromptId);
    if (newPrompt) {
      setSelectedPrompt(newPrompt);
      setPromptId(newPrompt.id);
      const template = newPrompt.parameters?.template || "";
      const tokenCount = Math.ceil(template.length / 4);
      onTokenCountChange?.(tokenCount);
    }

    setNewPromptModalOpen(false);
  }, [setPromptId, onTokenCountChange]);

  if (loading) {
    return null;
  }

  return (
    <>
      {/* Prompt Selection */}
      <Box sx={{ mb: 3 }}>
        <Autocomplete
          options={prompts}
          value={selectedPrompt}
          onChange={handlePromptChange}
          getOptionLabel={(option) => option.name || ""}
          isOptionEqualToValue={(option, value) => option?.id === value?.id}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("generative:simplifiedRag.prompt.selectTemplate")}
              placeholder={t("generative:simplifiedRag.prompt.selectTemplatePlaceholder")}
            />
          )}
          sx={{
            "& .MuiAutocomplete-option": {
              fontSize: "0.875rem",
            },
          }}
        />
      </Box>

      {/* Selected Prompt Info */}
      {selectedPrompt && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ mb: 2 }}>
            <strong>{t("generative:simplifiedRag.prompt.selectedTemplate")}</strong>
          </Typography>

          <Box
            sx={{
              p: 2,
              backgroundColor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 1,
              fontFamily: "monospace",
              fontSize: "0.875rem",
              lineHeight: 1.6,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              mb: 2,
            }}
          >
            {renderTemplateWithHighlights(selectedPrompt.parameters?.template || selectedPrompt.name)}
          </Box>

          {getDescription(selectedPrompt.description, i18n) && (
            <Typography variant="caption" display="block" sx={{ color: "text.secondary" }}>
              {getDescription(selectedPrompt.description, i18n)}
            </Typography>
          )}
        </Box>
      )}

      {/* New Prompt Button */}
      <Button
        variant="contained"
        fullWidth
        color="primary"
        size="large"
        startIcon={<AddIcon />}
        onClick={() => setNewPromptModalOpen(true)}
      >
        {t("generative:simplifiedRag.prompt.newPromptButton")}
      </Button>

      {/* Advanced Configuration Modal */}
      {selectedPrompt && (
        <PromptAdvancedModal
          open={showAdvanced}
          onClose={() => setShowAdvanced(false)}
          selectedPrompt={selectedPrompt}
          promptId={promptId}
          setPromptId={setPromptId}
        />
      )}

      {/* New Prompt Modal */}
      <NewPromptModal
        open={newPromptModalOpen}
        handleClose={() => setNewPromptModalOpen(false)}
        onPromptCreated={handlePromptCreated}
        existingPrompts={prompts}
      />
    </>
  );
}

PromptBody.propTypes = {
  promptId: PropTypes.number,
  setPromptId: PropTypes.func.isRequired,
  onTokenCountChange: PropTypes.func,
};
