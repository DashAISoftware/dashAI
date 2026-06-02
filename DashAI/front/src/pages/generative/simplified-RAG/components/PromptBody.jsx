import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
  MenuItem,
} from "@mui/material";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getRAGPrompts, getDefaultPrompts } from "../../../../api/rag";
import PromptAdvancedModal from "../advanced/PromptAdvancedModal";
import NewPromptModal from "../advanced/NewPromptModal";
import { getDescription, renderTemplateWithHighlights } from "./sectionUtils";

const LANGUAGE_OPTIONS = [
  { code: "en", name: "English" },
  { code: "es", name: "Español" },
  { code: "pt", name: "Português" },
];

const CREATE_NEW_ID = "__create-new__";
const DEFAULT_IDS = {
  DefaultRAGGenerationPrompt: "default-generation",
  DefaultQnARAGenerationPrompt: "default-qna",
};

function getDefaultDisplayName(component, t) {
  if (component.name === "DefaultRAGGenerationPrompt") {
    return t("generative:simplifiedRag.prompt.defaultGenerationPrompt");
  }
  if (component.name === "DefaultQnARAGenerationPrompt") {
    return t("generative:simplifiedRag.prompt.defaultQnAGenerationPrompt");
  }
  return component.name;
}

function getOptionLabel(option, t) {
  if (option._isCreateNew) return option.name;
  if (option._isDefault) return getDefaultDisplayName(option, t);
  return option.name;
}

export default function PromptBody({
  promptModel,
  setPromptModel,
  onTokenCountChange,
  showDetails = true,
}) {
  const { t, i18n } = useTranslation(["generative"]);
  const [customPrompts, setCustomPrompts] = useState([]);
  const [defaultPrompts, setDefaultPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newPromptModalOpen, setNewPromptModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState("en");
  const prevSelectedRef = useRef(null);

  const loadPrompts = useCallback(async () => {
    try {
      const customData = await getRAGPrompts();
      setCustomPrompts(customData || []);
    } catch (error) {
      console.error("Error loading custom RAG prompts:", error);
      setCustomPrompts([]);
    }

    try {
      const defaultData = await getDefaultPrompts();
      setDefaultPrompts(defaultData || []);
    } catch (error) {
      console.error("Error loading default RAG prompts:", error);
      setDefaultPrompts([]);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      await loadPrompts();
      setLoading(false);
    };
    load();
  }, [loadPrompts]);

  const mergedOptions = useMemo(() => {
    const defaults = defaultPrompts.map((dp) => ({
      ...dp,
      id: DEFAULT_IDS[dp.name] || dp.name,
      _isDefault: true,
      class_name: dp.name,
    }));
    const customs = customPrompts.map((cp) => ({
      ...cp,
      _isDefault: false,
    }));
    return [
      ...defaults,
      ...customs,
      {
        id: CREATE_NEW_ID,
        name: t("generative:simplifiedRag.prompt.createNewPrompt"),
        _isCreateNew: true,
        _isDefault: false,
        class_name: "",
      },
    ];
  }, [defaultPrompts, customPrompts, t]);

  const currentTemplate = useMemo(() => {
    if (!selectedPrompt) return "";
    if (selectedPrompt._isDefault) {
      return selectedPrompt.metadata?.templates?.[selectedLanguage] || "";
    }
    if (selectedPrompt.parameters?.templates) {
      return selectedPrompt.parameters.templates[selectedLanguage] || "";
    }
    return selectedPrompt.parameters?.template || "";
  }, [selectedPrompt, selectedLanguage]);

  const isDefault = selectedPrompt?._isDefault;

  useEffect(() => {
    if (selectedPrompt) {
      const promptParams = {
        template: currentTemplate,
        language: selectedLanguage,
      };
      const srcParams = selectedPrompt.parameters;
      if (selectedPrompt._isDefault || srcParams?.templates) {
        promptParams.templates = srcParams?.templates;
      }
      setPromptModel({
        component: selectedPrompt.class_name || selectedPrompt.name,
        params: promptParams,
      });
      if (onTokenCountChange) {
        const tokenCount = Math.ceil(currentTemplate.length / 4);
        onTokenCountChange(tokenCount);
      }
    } else {
      if (onTokenCountChange) {
        onTokenCountChange(0);
      }
    }
  }, [selectedPrompt, selectedLanguage]);

  useEffect(() => {
    const selectable = mergedOptions.filter((o) => !o._isCreateNew);
    if (!selectable.length) return;

    if (promptModel?.component) {
      const found = selectable.find((p) => {
        if (p._isDefault) {
          return p.class_name === promptModel.component;
        }
        return (
          p.class_name === promptModel.component &&
          p.parameters?.template === promptModel.params?.template
        );
      });
      setSelectedPrompt(found || null);
      prevSelectedRef.current = found || null;
      if (found?._isDefault) {
        setSelectedLanguage(promptModel.params?.language || "en");
      }
      return;
    }

    if (!selectedPrompt) {
      const firstDefault =
        selectable.find((p) => p._isDefault) || selectable[0];
      if (firstDefault) {
        setSelectedPrompt(firstDefault);
        setSelectedLanguage("en");
        prevSelectedRef.current = firstDefault;
      }
    }
  }, [mergedOptions, promptModel]);

  const handlePromptChange = (_event, newValue) => {
    if (newValue?._isCreateNew) {
      setNewPromptModalOpen(true);
      setSelectedPrompt(prevSelectedRef.current);
      return;
    }
    prevSelectedRef.current = newValue;
    setSelectedPrompt(newValue);
    if (newValue?._isDefault) {
      setSelectedLanguage("en");
    }
  };

  const handleLanguageChange = (event) => {
    setSelectedLanguage(event.target.value);
  };

  const handlePromptCreated = useCallback(
    async (newPromptId) => {
      const updatedPrompts = await getRAGPrompts();
      setCustomPrompts(updatedPrompts || []);

      const newPrompt = (updatedPrompts || []).find(
        (p) => p.id === newPromptId,
      );
      if (newPrompt) {
        const wrapped = { ...newPrompt, _isDefault: false };
        setSelectedPrompt(wrapped);
        prevSelectedRef.current = wrapped;
        const template = newPrompt.parameters?.template || "";
        const tokenCount = Math.ceil(template.length / 4);
        onTokenCountChange?.(tokenCount);
      }

      setNewPromptModalOpen(false);
    },
    [onTokenCountChange],
  );

  const advancedPromptData = useMemo(() => {
    if (!selectedPrompt) return null;
    return {
      ...selectedPrompt,
      template: currentTemplate,
    };
  }, [selectedPrompt, currentTemplate]);

  if (loading) {
    return null;
  }

  return (
    <>
      <Box sx={{ mb: isDefault && showDetails ? 2 : showDetails ? 3 : 0 }}>
        <Autocomplete
          options={mergedOptions}
          value={selectedPrompt}
          onChange={handlePromptChange}
          getOptionLabel={(option) => getOptionLabel(option, t)}
          isOptionEqualToValue={(option, value) => option.id === value.id}
          renderOption={(props, option) => (
            <li {...props}>{getOptionLabel(option, t)}</li>
          )}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("generative:simplifiedRag.prompt.selectTemplate")}
              placeholder={t(
                "generative:simplifiedRag.prompt.selectTemplatePlaceholder",
              )}
            />
          )}
          sx={{
            "& .MuiAutocomplete-option": {
              fontSize: "0.875rem",
            },
          }}
        />
      </Box>

      {(isDefault || selectedPrompt?.parameters?.templates) && showDetails && (
        <Box sx={{ mb: 2 }}>
          <TextField
            select
            fullWidth
            label={t("generative:simplifiedRag.prompt.language")}
            value={selectedLanguage}
            onChange={handleLanguageChange}
            size="small"
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <MenuItem key={opt.code} value={opt.code}>
                {opt.name}
              </MenuItem>
            ))}
          </TextField>
        </Box>
      )}

      {showDetails && selectedPrompt && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ mb: 2 }}>
            <strong>
              {t("generative:simplifiedRag.prompt.selectedTemplate")}
            </strong>
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
            {renderTemplateWithHighlights(currentTemplate)}
          </Box>

          {getDescription(selectedPrompt.description, i18n) && (
            <Typography
              variant="caption"
              display="block"
              sx={{ color: "text.secondary" }}
            >
              {getDescription(selectedPrompt.description, i18n)}
            </Typography>
          )}
        </Box>
      )}

      {showDetails && (
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
      )}

      {advancedPromptData && (
        <PromptAdvancedModal
          open={showAdvanced}
          onClose={() => setShowAdvanced(false)}
          selectedPrompt={advancedPromptData}
          promptId={advancedPromptData.id}
          setPromptId={() => {}}
        />
      )}

      <NewPromptModal
        open={newPromptModalOpen}
        handleClose={() => setNewPromptModalOpen(false)}
        onPromptCreated={handlePromptCreated}
        existingPrompts={customPrompts}
      />
    </>
  );
}

PromptBody.propTypes = {
  promptModel: PropTypes.shape({
    component: PropTypes.string,
    params: PropTypes.shape({
      template: PropTypes.string,
      language: PropTypes.string,
    }),
  }),
  setPromptModel: PropTypes.func.isRequired,
  onTokenCountChange: PropTypes.func,
  showDetails: PropTypes.bool,
};
