import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Paper,
  Autocomplete,
  TextField,
  Button,
  CircularProgress,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getRAGPrompts } from "../../../../api/rag";
import PromptAdvancedModal from "../advanced/PromptAdvancedModal";

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
}) {
  const { i18n } = useTranslation();
  const [prompts, setPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPrompts = async () => {
      try {
        const data = await getRAGPrompts();
        setPrompts(data || []);

        if (data && data.length > 0) {
          if (promptId) {
            const found = data.find((p) => p.id === promptId);
            if (found) {
              setSelectedPrompt(found);
            }
          } else {
            // Select first prompt by default if none selected
            setSelectedPrompt(data[0]);
            setPromptId(data[0].id);
          }
        }
      } catch (error) {
        console.error("Error loading RAG prompts:", error);
      } finally {
        setLoading(false);
      }
    };
    loadPrompts();
  }, []);

  const handlePromptChange = (event, newValue) => {
    setSelectedPrompt(newValue);
    if (newValue) {
      setPromptId(newValue.id);
    } else {
      setPromptId(null);
    }
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3, backgroundColor: "background.paper" }}>
        <Box display="flex" justifyContent="center" alignItems="center" sx={{ minHeight: 200 }}>
          <CircularProgress />
        </Box>
      </Paper>
    );
  }

  return (
    <>
      <Paper sx={{ p: 3, backgroundColor: "background.paper" }}>

        <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
          Select a prompt template that defines how the retrieved context and
          chat messages are combined to generate responses.
        </Typography>

        {/* Prompt Selection */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
            Available Prompts
          </Typography>
          <Autocomplete
            options={prompts}
            value={selectedPrompt}
            onChange={handlePromptChange}
            getOptionLabel={(option) => option.name || ""}
            isOptionEqualToValue={(option, value) => option?.id === value?.id}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Select prompt template"
                placeholder="e.g., Default Prompt, Custom Instruction"
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
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              mb: 3,
              backgroundColor: "action.hover",
              borderColor: "divider",
            }}
          >
            <Typography variant="body2" sx={{ mb: 2 }}>
              <strong>Selected Prompt Template:</strong>
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
          </Paper>
        )}

        {/* Advanced Configuration Button */}
        <Button
          variant="outlined"
          color="primary"
          onClick={() => setShowAdvanced(true)}
          fullWidth
          sx={{ mt: 2 }}
          disabled={!selectedPrompt}
        >
          ↗ Open Advanced Configuration
        </Button>
      </Paper>

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
    </>
  );
}

PromptSection.propTypes = {
  promptId: PropTypes.number,
  setPromptId: PropTypes.func.isRequired,
};
