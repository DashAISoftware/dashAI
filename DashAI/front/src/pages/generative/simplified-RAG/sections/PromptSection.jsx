import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Autocomplete,
  TextField,
  Button,
  CircularProgress,
  Collapse,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { ViewList as ViewListIcon, AddCircleOutline as AddIcon, Info as InfoIcon, ExpandMore as ExpandMoreIcon } from "@mui/icons-material";
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getRAGPrompts } from "../../../../api/rag";
import PromptAdvancedModal from "../advanced/PromptAdvancedModal";
import NewPromptModal from "../advanced/NewPromptModal";

const getDescription = (desc, i18n) => {
  if (!desc) return "";
  if (typeof desc === "string") return desc;
  if (typeof desc === "object" && (desc.en || desc.es)) {
    return desc[i18n.language] || desc.en || desc.es || "";
  }
  return "";
};

const renderTemplateWithHighlights = (template) => {
  if (!template) return null;
  
  // Regex to find placeholders like {input}, {chunks}, {context}, etc.
  const placeholderRegex = /\{([^}]+)\}/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = placeholderRegex.exec(template)) !== null) {
    // Add text before the placeholder
    if (match.index > lastIndex) {
      parts.push(template.substring(lastIndex, match.index));
    }
    
    // Add highlighted placeholder
    parts.push({
      type: "placeholder",
      value: match[0],
      label: match[1],
    });
    
    lastIndex = placeholderRegex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < template.length) {
    parts.push(template.substring(lastIndex));
  }

  return parts.map((part, idx) => {
    if (typeof part === "string") {
      return <span key={idx}>{part}</span>;
    }
    return (
      <Box
        component="span"
        key={idx}
        sx={{
          backgroundColor: "warning.light",
          color: "warning.dark",
          padding: "2px 4px",
          borderRadius: "3px",
          fontWeight: 600,
          fontFamily: "monospace",
        }}
      >
        {part.value}
      </Box>
    );
  });
};

export default function PromptSection({
  promptId,
  setPromptId,
  onTokenCountChange,
}) {
  const navigate = useNavigate();
  const goToPromptsDetail = () => navigate('/app/generative/rag/prompts');
  const { t, i18n } = useTranslation(["generative"]);
  const [prompts, setPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newPromptModalOpen, setNewPromptModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showDescription, setShowDescription] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  // Stable callback to load prompts
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
      // Select first prompt by default if none selected
      setSelectedPrompt(prompts[0]);
      setPromptId(prompts[0].id);
    }
  }, [prompts, promptId, selectedPrompt, setPromptId]);

  useEffect(() => {
    if (selectedPrompt && onTokenCountChange) {
      const template = selectedPrompt.parameters?.template || '';
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
      const template = newValue.parameters?.template || '';
      const tokenCount = Math.ceil(template.length / 4);  // Estimación simple
      onTokenCountChange?.(tokenCount);  // Notificar al padre
    } else {
      setPromptId(null);
      onTokenCountChange?.(0);
    }
  };

  // Handle new prompt creation
  const handlePromptCreated = useCallback(async (newPromptId) => {
    // Reload prompts to get the new one
    const updatedPrompts = await getRAGPrompts();
    setPrompts(updatedPrompts || []);
    
    // Find and select the new prompt
    const newPrompt = (updatedPrompts || []).find((p) => p.id === newPromptId);
    if (newPrompt) {
      setSelectedPrompt(newPrompt);
      setPromptId(newPrompt.id);
      const template = newPrompt.parameters?.template || '';
      const tokenCount = Math.ceil(template.length / 4);
      onTokenCountChange?.(tokenCount);
    }
    
    setNewPromptModalOpen(false);
  }, [setPromptId, onTokenCountChange]);

  if (loading) {
    return (
      <Card sx={{ backgroundColor: "background.paper" }}>
        <Box display="flex" justifyContent="center" alignItems="center" sx={{ minHeight: 200 }}>
          <CircularProgress />
        </Box>
      </Card>
    );
  }

  return (
    <>
      <Card sx={{ backgroundColor: "background.paper" }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Prompt</Typography>
              <Box>
                <Tooltip title={t("generative:simplifiedRag.prompt.descriptionToggle") || "Description"}>
                  <IconButton
                    size="small"
                    onClick={() => setShowDescription((s) => !s)}
                    aria-label="prompt-info"
                    sx={{ color: 'text.secondary' }}
                  >
                    <InfoIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title={t("generative:simplifiedRag.prompt.openPrompts")}>
                  <IconButton size="small" onClick={goToPromptsDetail} aria-label="open-prompt-library">
                    <ViewListIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title={isExpanded ? (t("generative:simplifiedRag.prompt.collapse") || "Collapse") : (t("generative:simplifiedRag.prompt.expand") || "Expand")}>
                  <IconButton
                    size="small"
                    onClick={() => setIsExpanded((s) => !s)}
                    aria-label="toggle-prompt-card"
                  >
                    <ExpandMoreIcon
                      fontSize="small"
                      sx={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
                    />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
            {showDescription && (
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                {t("generative:simplifiedRag.prompt.description")}
              </Typography>
            )}
          </Box>

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

            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
              <Box>

            {/* Selected Prompt Info */}
            {selectedPrompt && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  <strong>{t("generative:simplifiedRag.prompt.selectedTemplate")}</strong>
                </Typography>

                {/* Template Display with Highlighted Placeholders */}
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

                {/* Prompt Description */}
                {getDescription(selectedPrompt.description, i18n) && (
                  <Typography variant="caption" display="block" sx={{ color: "text.secondary" }}>
                    {getDescription(selectedPrompt.description, i18n)}
                  </Typography>
                )}
              </Box>
            )}

            {/* Advanced Configuration Button */}
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
            </Box>
          </Collapse>
        </CardContent>
      </Card>

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


PromptSection.propTypes = {
  promptId: PropTypes.number,
  setPromptId: PropTypes.func.isRequired,
};
