import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
  MenuItem,
  useTheme,
} from "@mui/material";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  getRAGPrompts,
  getDefaultPrompts,
  isGenerationPromptClass,
} from "../../../../api/rag";
import NewPromptModal from "../advanced/NewPromptModal";
import RAGSectionColumn from "../components/RAGSectionColumn";
import { getDescription, renderTemplateWithHighlights } from "../components/sectionUtils";

import { LANGUAGE_CODES } from "../../../../constants/languages";

const CREATE_NEW_ID = "__create-new__";
const DEFAULT_IDS = {
  DefaultRAGGenerationPrompt: "default-generation",
  DefaultQARAGGenerationPrompt: "default-QA",
};

function getDefaultDisplayName(option, t) {
  // Use class_name (set explicitly by our code) rather than name
  // (raw API field) to avoid potential encoding / serialization mismatches.
  const cname = option.class_name || option.name || "";
  if (cname.includes("DefaultQARAGGenerationPrompt")) {
    return t("generative:rag.prompt.defaultQAGenerationPrompt");
  }
  if (cname.includes("DefaultRAGGenerationPrompt")) {
    return t("generative:rag.prompt.defaultGenerationPrompt");
  }
  return option.name || cname;
}

function getOptionLabel(option, t) {
  if (option._isCreateNew) return option.name;
  if (option._isDefault) return getDefaultDisplayName(option, t);
  return option.name;
}

export default function PromptSection({
  promptModel,
  setPromptModel,
  onTokenCountChange,
}) {
  const { t, i18n } = useTranslation(["generative"]);
  const theme = useTheme();
  const placeholderColors = useMemo(
    () => ({
      bg: theme.palette.placeholder?.bg || theme.palette.warning.light,
      text: theme.palette.placeholder?.text || theme.palette.warning.dark,
    }),
    [theme],
  );
  const platformLang = useMemo(() => {
    const lang = (i18n.language || "en").split("-")[0];
    return ["en", "es", "pt"].includes(lang) ? lang : "en";
  }, [i18n.language]);
  const [customPrompts, setCustomPrompts] = useState([]);
  const [defaultPrompts, setDefaultPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [newPromptModalOpen, setNewPromptModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState(platformLang);
  const prevSelectedRef = useRef(null);
  const isInitializedRef = useRef(false);

  const loadPrompts = useCallback(async () => {
    try {
      const dbPrompts = await getRAGPrompts();
      // Keep only user-created generation prompts:
      // 1. Exclude system defaults (class_name starts with "Default")
      // 2. Exclude augmentation prompts (wrong type for this selector)
      setCustomPrompts(
        (dbPrompts || []).filter(
          (p) =>
            !p.class_name.startsWith("Default") &&
            isGenerationPromptClass(p.class_name),
        ),
      );
    } catch (error) {
      console.error("Error loading custom RAG prompts:", error);
      setCustomPrompts([]);
    }

    try {
      const defaultData = await getDefaultPrompts();
      // Filter out CustomRAGGenerationPrompt — it's a base class for
      // user-created prompts, not a selectable template. It has no
      // templates in its metadata and inherits a generic description
      // ("Base class for RAG prompts.") from Prompt.
      setDefaultPrompts(
        (defaultData || []).filter(
          (dp) => dp.name !== "CustomRAGGenerationPrompt",
        ),
      );
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
        name: t("generative:rag.prompt.createNewPrompt"),
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
    if (!selectedPrompt) {
      if (onTokenCountChange) onTokenCountChange(0);
      return;
    }

    if (!isInitializedRef.current && promptModel?.component === (selectedPrompt.class_name || selectedPrompt.name)) {
      isInitializedRef.current = true;
      return;
    }
    isInitializedRef.current = true;

    setPromptModel({
      component: selectedPrompt.class_name || selectedPrompt.name,
      params: {
        template: currentTemplate,
        language: selectedLanguage,
        ...(selectedPrompt._isDefault || selectedPrompt.parameters?.templates
          ? { templates: selectedPrompt.parameters?.templates }
          : {}),
      },
    });
    if (onTokenCountChange) {
      const tokenCount = Math.ceil(currentTemplate.length / 4);
      onTokenCountChange(tokenCount);
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
      if (found?.id !== selectedPrompt?.id) {
        setSelectedPrompt(found || null);
        prevSelectedRef.current = found || null;
        if (found?._isDefault) {
          setSelectedLanguage(promptModel.params?.language || platformLang);
        }
        isInitializedRef.current = false;
      }
      return;
    }

    if (!selectedPrompt) {
      const firstDefault =
        selectable.find((p) => p._isDefault) || selectable[0];
      if (firstDefault) {
        setSelectedPrompt(firstDefault);
        setSelectedLanguage(platformLang);
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
      setSelectedLanguage(platformLang);
    }
  };

  const handleLanguageChange = (event) => {
    setSelectedLanguage(event.target.value);
  };

  const handlePromptCreated = useCallback(
    async (newPromptId) => {
      const updatedPrompts = await getRAGPrompts();
      // Apply same filter as loadPrompts: exclude system defaults and augmentation
      setCustomPrompts(
        (updatedPrompts || []).filter(
          (p) =>
            !p.class_name.startsWith("Default") &&
            isGenerationPromptClass(p.class_name),
        ),
      );

      const newPrompt = (updatedPrompts || []).find(
        (p) => p.id === newPromptId,
      );
      if (newPrompt) {
        const wrapped = { ...newPrompt, _isDefault: false };
        setSelectedPrompt(wrapped);
        prevSelectedRef.current = wrapped;
        // Sync language from the newly created prompt's saved language
        // so local selectedLanguage stays aligned with the persisted value.
        if (newPrompt.parameters?.language) {
          setSelectedLanguage(newPrompt.parameters.language);
        }
        // Sync parent promptModel immediately to prevent infinite
        // useEffect 1 <-> useEffect 2 ping-pong when the new prompt's
        // class_name differs from the previously selected prompt.
        setPromptModel({
          component: newPrompt.class_name,
          params: {
            template: newPrompt.parameters?.template || "",
            language: newPrompt.parameters?.language || "",
          },
        });
        const template = newPrompt.parameters?.template || "";
        const tokenCount = Math.ceil(template.length / 4);
        onTokenCountChange?.(tokenCount);
      }

      setNewPromptModalOpen(false);
    },
    [onTokenCountChange, setPromptModel],
  );

  if (loading) {
    return null;
  }

  return (
    <RAGSectionColumn>
      <Typography variant="body2" color="textSecondary">
        {t("generative:rag.prompt.description")}
      </Typography>

            <Button
        variant="contained"
        color="primary"
        size="small"
        startIcon={<AddIcon />}
        onClick={() => setNewPromptModalOpen(true)}
        sx={{
          alignSelf: "flex-start", 
          width: "fit-content",
          border: "1px solid",
          borderColor: theme.palette.primary.main,
          backgroundColor: theme.palette.action.selected,
          color: theme.palette.text.primary,
        }}
      >
        {t("generative:rag.prompt.newPromptButton")}
      </Button>

      <Box>
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
              label={t("generative:rag.prompt.selectTemplate")}
              placeholder={t(
                "generative:rag.prompt.selectTemplatePlaceholder",
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

      {(isDefault || selectedPrompt?.parameters?.templates) && (
        <TextField
          select
          fullWidth
          label={t("generative:rag.prompt.language")}
          value={selectedLanguage}
          onChange={handleLanguageChange}
          size="small"
        >
          {LANGUAGE_CODES.map((code) => (
            <MenuItem key={code} value={code}>
              {t(`generative:rag.prompt.languages.${code}`)}
            </MenuItem>
          ))}
        </TextField>
      )}

      {selectedPrompt && (
        <RAGSectionColumn>
          <Typography variant="subtitle2" >
            {t("generative:rag.prompt.selectedTemplate")}
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
            }}
          >
            {renderTemplateWithHighlights(currentTemplate, placeholderColors)}
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
        </RAGSectionColumn>
      )}

      <NewPromptModal
        open={newPromptModalOpen}
        handleClose={() => setNewPromptModalOpen(false)}
        onPromptCreated={handlePromptCreated}
        existingPrompts={customPrompts}
      />
    </RAGSectionColumn>
  );
}

PromptSection.propTypes = {
  promptModel: PropTypes.shape({
    component: PropTypes.string,
    params: PropTypes.shape({
      template: PropTypes.string,
      language: PropTypes.string,
    }),
  }),
  setPromptModel: PropTypes.func.isRequired,
  onTokenCountChange: PropTypes.func,
};
