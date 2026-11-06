import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { useTranslation } from "react-i18next";
import HighlightedTextarea from "./HighlightedTextarea";
import PlaceholdersList from "./PlaceholdersList";
import RAGAdvancedDialog from "../../../pages/generative/RAGSession/advanced/RAGAdvancedDialog";
import { getDefaultPrompts, getLibraryPrompts } from "../../../api/rag";
import { getChildComponents } from "../../../api/component";
import { LANGUAGE_CODES } from "../../../constants/languages";

/** The component a hand-written template is stored under. */
const CUSTOM_PROMPT_COMPONENT = "CustomRAGGenerationPrompt";

/**
 * Placeholders every RAG prompt has to contain, used until the registry's own
 * answer arrives (and if that request fails).
 */
const FALLBACK_REQUIRED = ["{chunks}", "{input}"];

/**
 * The prompt of one RAG session, edited in place.
 *
 * This replaced a picker over a shared prompt library. Prompt rows are
 * deduplicated by a hash of their parameters, so two sessions that chose the
 * same template shared one row: editing it rewrote the other session's prompt.
 * The template now lives in the session's own parameters, and the registry's
 * built-in templates are only ever used to seed it.
 *
 * Nothing is sent while typing. The panel's Save writes the whole draft, so a
 * half-finished template never reaches the pipeline.
 *
 * @param {object}   props
 * @param {object}   props.promptModel - The draft `{component, params}` ref.
 * @param {Function} props.setPromptModel - Replaces the draft ref.
 * @param {Function} [props.onValidityChange] - Called with whether the
 *   template has every required placeholder.
 * @returns {JSX.Element} The editor.
 */
export default function PromptEditor({
  promptModel,
  setPromptModel,
  onValidityChange,
  showSeeding = true,
  componentName = CUSTOM_PROMPT_COMPONENT,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const [seeds, setSeeds] = useState([]);
  const [savedPrompts, setSavedPrompts] = useState([]);
  const [placeholderSpec, setPlaceholderSpec] = useState({
    required: FALLBACK_REQUIRED,
    optional: [],
    descriptions: {},
  });
  const [expanded, setExpanded] = useState(false);
  const textareaRef = useRef(null);
  const dialogTextareaRef = useRef(null);
  const componentNameRef = useRef(componentName);
  const generationMetadataRef = useRef(null);
  useEffect(() => {
    componentNameRef.current = componentName;
  }, [componentName]);

  const template = promptModel?.params?.template ?? "";
  // Which language's template to seed from. `CustomRAGGenerationPrompt` takes
  // only a template and never reads a language, so storing one in its params
  // would be a control that silently does nothing.
  const [seedLanguage, setSeedLanguage] = useState(
    promptModel?.params?.language ?? "en",
  );

  useEffect(() => {
    if (!showSeeding) return undefined;
    let cancelled = false;
    getLibraryPrompts()
      .then((options) => {
        // Built-in templates are already offered by the "Start from" select;
        // only user-saved prompts belong in the second one.
        if (!cancelled) {
          setSavedPrompts(options.filter((prompt) => prompt.is_library));
        }
      })
      .catch((error) => {
        console.error("Failed to load saved prompts:", error);
        if (!cancelled) setSavedPrompts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [showSeeding]);

  useEffect(() => {
    let cancelled = false;
    getDefaultPrompts()
      .then((options) => {
        if (cancelled) return;
        // CustomRAGGenerationPrompt is the base class a hand-written template
        // is stored under, not a template to start from.
        setSeeds(options.filter((o) => o.name !== CUSTOM_PROMPT_COMPONENT));
        const base = options.find((o) => o.name === CUSTOM_PROMPT_COMPONENT);
        if (base?.metadata) {
          generationMetadataRef.current = base.metadata;
          if (componentNameRef.current === CUSTOM_PROMPT_COMPONENT) {
            setPlaceholderSpec({
              required:
                base.metadata.required_placeholders ?? FALLBACK_REQUIRED,
              optional: base.metadata.optional_placeholders ?? [],
              descriptions: base.metadata.placeholder_descriptions ?? {},
            });
          }
        }
      })
      .catch((error) => {
        console.error("Failed to load prompt templates:", error);
        if (!cancelled) setSeeds([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (componentName === CUSTOM_PROMPT_COMPONENT) {
      const metadata = generationMetadataRef.current;
      setPlaceholderSpec({
        required: metadata?.required_placeholders ?? FALLBACK_REQUIRED,
        optional: metadata?.optional_placeholders ?? [],
        descriptions: metadata?.placeholder_descriptions ?? {},
      });
      return undefined;
    }
    let cancelled = false;
    getChildComponents("BasePrompt", true)
      .then((components) => {
        if (cancelled) return;
        const selected = components.find(
          (component) => component.name === componentName,
        );
        const metadata = selected?.metadata;
        if (!metadata) return;
        setPlaceholderSpec({
          required: metadata.required_placeholders ?? FALLBACK_REQUIRED,
          optional: metadata.optional_placeholders ?? [],
          descriptions: metadata.placeholder_descriptions ?? {},
        });
      })
      .catch((error) => {
        console.error("Failed to load placeholder metadata:", error);
      });
    return () => {
      cancelled = true;
    };
  }, [componentName]);

  const missing = useMemo(
    () => placeholderSpec.required.filter((ph) => !template.includes(ph)),
    [placeholderSpec, template],
  );

  useEffect(() => {
    onValidityChange?.(missing.length === 0);
  }, [missing, onValidityChange]);

  const update = useCallback(
    (nextTemplate) => {
      setPromptModel({
        component: componentName,
        params: { template: nextTemplate },
      });
    },
    [componentName, setPromptModel],
  );

  /**
   * Replaces the template with a registry template.
   *
   * Seeding is explicit rather than a side effect of picking a language: the
   * language select used to silently overwrite whatever the user had written.
   *
   * @param {string} name - The seed component's name.
   */
  const handleSeed = (name) => {
    const seed = seeds.find((option) => option.name === name);
    const seeded = seed?.metadata?.templates?.[seedLanguage];
    if (seeded === undefined) return;
    update(seeded);
  };

  /**
   * Replaces the template with one saved in the prompt library.
   *
   * @param {string} value - The selected prompt id, as a string.
   */
  const handleSeedSaved = (value) => {
    const prompt = savedPrompts.find((item) => String(item.id) === value);
    if (!prompt) return;
    const parameters = prompt.parameters ?? {};
    const templates = parameters.templates ?? {};
    const templateText =
      parameters.template ??
      templates[seedLanguage] ??
      Object.values(templates)[0];
    if (typeof templateText !== "string") return;
    update(templateText);
    if (parameters.language) setSeedLanguage(parameters.language);
  };

  const insertPlaceholder = useCallback(
    (placeholder) => {
      const textarea = expanded
        ? dialogTextareaRef.current
        : textareaRef.current;
      if (!textarea) {
        update(template + placeholder);
        return;
      }
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const next =
        template.substring(0, start) + placeholder + template.substring(end);
      update(next);
      requestAnimationFrame(() => {
        const position = start + placeholder.length;
        textarea.selectionStart = position;
        textarea.selectionEnd = position;
        textarea.focus();
      });
    },
    [expanded, template, update],
  );

  const editor = (ref, minRows) => (
    <HighlightedTextarea
      ref={ref}
      value={template}
      onChange={(event) => update(event.target.value)}
      minRows={minRows}
      placeholder={t("generative:rag.prompt.editor.templatePlaceholder")}
    />
  );

  return (
    <Stack spacing={2}>
      {showSeeding && (
        <>
          <Stack direction="row" spacing={1}>
            <TextField
              select
              size="small"
              fullWidth
              label={t("generative:rag.prompt.editor.startFrom")}
              value=""
              onChange={(event) => handleSeed(event.target.value)}
              helperText={t("generative:rag.prompt.editor.startFromHelp")}
            >
              {seeds.map((seed) => (
                <MenuItem key={seed.name} value={seed.name}>
                  {seed.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label={t("generative:rag.prompt.editor.seedLanguage")}
              value={seedLanguage}
              onChange={(event) => setSeedLanguage(event.target.value)}
              sx={{ minWidth: 96 }}
            >
              {LANGUAGE_CODES.map((code) => (
                <MenuItem key={code} value={code}>
                  {code}
                </MenuItem>
              ))}
            </TextField>
          </Stack>

          {savedPrompts.length > 0 && (
            <TextField
              select
              size="small"
              fullWidth
              label={t("generative:rag.prompt.editor.savedPrompt")}
              value=""
              onChange={(event) => handleSeedSaved(event.target.value)}
              helperText={t("generative:rag.prompt.editor.savedPromptHelp")}
            >
              {savedPrompts.map((prompt) => (
                <MenuItem key={prompt.id} value={String(prompt.id)}>
                  {prompt.name || `Prompt ${prompt.id}`}
                </MenuItem>
              ))}
            </TextField>
          )}
        </>
      )}

      <PlaceholdersList
        required={placeholderSpec.required}
        optional={placeholderSpec.optional}
        descriptions={placeholderSpec.descriptions}
        template={template}
        onInsertPlaceholder={insertPlaceholder}
      />

      <Box>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
        >
          <Typography variant="subtitle2">
            {t("generative:rag.prompt.editor.template")}
          </Typography>
          <Tooltip title={t("generative:rag.prompt.editor.expand")}>
            <IconButton
              size="small"
              onClick={() => setExpanded(true)}
              aria-label={t("generative:rag.prompt.editor.expand")}
            >
              <OpenInFullIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
        {editor(textareaRef, 8)}
      </Box>

      {missing.length > 0 && (
        <Alert severity="error" sx={{ py: 0.5 }}>
          {t("generative:rag.prompt.editor.missingPlaceholder", {
            placeholders: missing.join(", "),
          })}
        </Alert>
      )}

      {/* The same controlled state, with room to read: eight rows in a panel
          this narrow is not enough for a real prompt. Dressed like the
          module's other advanced editors through the shared RAG shell. */}
      <RAGAdvancedDialog
        open={expanded}
        onClose={() => setExpanded(false)}
        title={t("generative:rag.prompt.editor.template")}
        contentSx={{ minHeight: 400 }}
        actions={
          <>
            <Button onClick={() => setExpanded(false)} variant="outlined">
              {t("generative:rag.advanced.close")}
            </Button>
            <Button
              onClick={() => setExpanded(false)}
              variant="contained"
              color="primary"
              disabled={missing.length > 0}
            >
              {t("generative:rag.advanced.done")}
            </Button>
          </>
        }
      >
        <Stack spacing={2}>
          <PlaceholdersList
            required={placeholderSpec.required}
            optional={placeholderSpec.optional}
            descriptions={placeholderSpec.descriptions}
            template={template}
            onInsertPlaceholder={insertPlaceholder}
          />
          {editor(dialogTextareaRef, 18)}
          {missing.length > 0 && (
            <Alert severity="error" sx={{ py: 0.5 }}>
              {t("generative:rag.prompt.editor.missingPlaceholder", {
                placeholders: missing.join(", "),
              })}
            </Alert>
          )}
        </Stack>
      </RAGAdvancedDialog>
    </Stack>
  );
}

PromptEditor.propTypes = {
  promptModel: PropTypes.shape({
    component: PropTypes.string,
    params: PropTypes.object,
  }),
  setPromptModel: PropTypes.func.isRequired,
  onValidityChange: PropTypes.func,
  showSeeding: PropTypes.bool,
  componentName: PropTypes.string,
};
