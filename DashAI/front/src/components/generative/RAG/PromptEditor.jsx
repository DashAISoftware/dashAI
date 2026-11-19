import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  IconButton,
  ListSubheader,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import HighlightedTextarea from "./HighlightedTextarea";
import PlaceholdersList from "./PlaceholdersList";
import RAGAdvancedDialog from "../../../pages/generative/RAGSession/advanced/RAGAdvancedDialog";
import {
  createRAGPrompt,
  getDefaultPrompts,
  getLibraryPrompts,
} from "../../../api/rag";
import { getChildComponents } from "../../../api/component";
import { getApiErrorMessage } from "../../../utils/apiError";
import { LANGUAGE_CODES } from "../../../constants/languages";
import {
  DEFAULT_PROMPT_LANGUAGE,
  PROMPT_LANGUAGE_PARAM,
  resolveStoredPromptTemplate,
  storedPromptLanguages,
  storedPromptShape,
} from "./promptSchema";

/** The component a hand-written template is stored under. */
const CUSTOM_PROMPT_COMPONENT = "CustomRAGGenerationPrompt";

/**
 * A seed language the selector can actually display.
 *
 * The language saved with a prompt is not guaranteed to be one of the codes
 * this editor offers, and a select whose value is not an option renders empty.
 *
 * @param {*} candidate - The language to prefer, if any.
 * @returns {string} The candidate when it is selectable, the default otherwise.
 */
function selectableSeedLanguage(candidate) {
  return LANGUAGE_CODES.includes(candidate)
    ? candidate
    : DEFAULT_PROMPT_LANGUAGE;
}

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
  const { enqueueSnackbar } = useSnackbar();
  const [seeds, setSeeds] = useState([]);
  const [savedPrompts, setSavedPrompts] = useState([]);
  const [libraryVersion, setLibraryVersion] = useState(0);
  const [seedsLoaded, setSeedsLoaded] = useState(false);
  const [savedLoaded, setSavedLoaded] = useState(!showSeeding);
  // "" (nothing picked), `default:<component>` or `saved:<id>`.
  const [selection, setSelection] = useState("");
  const selectionInferredRef = useRef(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);
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
  const [seedLanguage, setSeedLanguage] = useState(() =>
    selectableSeedLanguage(promptModel?.params?.[PROMPT_LANGUAGE_PARAM]),
  );

  useEffect(() => {
    if (!showSeeding) return undefined;
    let cancelled = false;
    getLibraryPrompts()
      .then((options) => {
        // Built-in templates come from the registry; only user-saved prompts
        // belong here. This editor writes a generation template, so
        // query-rewriting or agentic retriever prompts would be loaded into a
        // slot that never runs them.
        if (!cancelled) {
          setSavedPrompts(
            options.filter(
              (prompt) =>
                prompt.is_library && prompt.prompt_type === "generation",
            ),
          );
          setSavedLoaded(true);
        }
      })
      .catch((error) => {
        console.error("Failed to load saved prompts:", error);
        if (!cancelled) {
          setSavedPrompts([]);
          setSavedLoaded(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [showSeeding, libraryVersion]);

  useEffect(() => {
    let cancelled = false;
    getDefaultPrompts()
      .then((options) => {
        if (cancelled) return;
        // CustomRAGGenerationPrompt is the base class a hand-written template
        // is stored under, not a template to start from.
        setSeeds(options.filter((o) => o.name !== CUSTOM_PROMPT_COMPONENT));
        setSeedsLoaded(true);
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
        if (!cancelled) {
          setSeeds([]);
          setSeedsLoaded(true);
        }
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

  /** Selectable languages a default prompt ships a template for. */
  const defaultLanguages = useCallback(
    (name) =>
      Object.keys(
        seeds.find((option) => option.name === name)?.metadata?.templates ?? {},
      ).filter((code) => LANGUAGE_CODES.includes(code)),
    [seeds],
  );

  /** The template a saved prompt loads, preferring `language`. */
  const savedTemplate = useCallback((prompt, language) => {
    const parameters = prompt.parameters ?? {};
    const shape = storedPromptShape(parameters);
    const languages = storedPromptLanguages(parameters).filter((code) =>
      LANGUAGE_CODES.includes(code),
    );
    if (shape.usesTemplates && languages.length === 0) return null;
    const preferred = languages.includes(language)
      ? language
      : languages.includes(shape.language)
        ? shape.language
        : (languages[0] ?? selectableSeedLanguage(language));
    const text = resolveStoredPromptTemplate(parameters, preferred);
    return text ? { text, language: selectableSeedLanguage(preferred) } : null;
  }, []);

  // Work out which prompt the incoming template came from, once, so the
  // selector opens on it instead of looking empty.
  useEffect(() => {
    if (selectionInferredRef.current || !seedsLoaded || !savedLoaded) return;
    selectionInferredRef.current = true;
    if (!showSeeding || !template) return;
    for (const seed of seeds) {
      const templates = seed.metadata?.templates ?? {};
      const code = Object.keys(templates).find(
        (language) =>
          LANGUAGE_CODES.includes(language) && templates[language] === template,
      );
      if (code) {
        setSelection(`default:${seed.name}`);
        setSeedLanguage(code);
        return;
      }
    }
    const saved = savedPrompts.find(
      (prompt) => savedTemplate(prompt, seedLanguage)?.text === template,
    );
    if (saved) setSelection(`saved:${saved.id}`);
  }, [
    seedsLoaded,
    savedLoaded,
    showSeeding,
    seeds,
    savedPrompts,
    template,
    seedLanguage,
    savedTemplate,
  ]);

  /**
   * Loads the chosen prompt, default or saved, into the editable template.
   *
   * @param {string} value - `default:<component>` or `saved:<id>`.
   */
  const handleSelectPrompt = (value) => {
    if (value.startsWith("default:")) {
      const name = value.slice("default:".length);
      const languages = defaultLanguages(name);
      const language = languages.includes(seedLanguage)
        ? seedLanguage
        : (languages[0] ?? seedLanguage);
      const seeded = seeds.find((option) => option.name === name)?.metadata
        ?.templates?.[language];
      if (seeded === undefined) return;
      setSelection(value);
      setSeedLanguage(language);
      update(seeded);
      return;
    }
    const prompt = savedPrompts.find((item) => `saved:${item.id}` === value);
    const loaded = prompt && savedTemplate(prompt, seedLanguage);
    if (!loaded) return;
    setSelection(value);
    setSeedLanguage(loaded.language);
    update(loaded.text);
  };

  /** Switches the selected default prompt to another language's template. */
  const handleLanguageChange = (language) => {
    setSeedLanguage(language);
    const name = selection.slice("default:".length);
    const seeded = seeds.find((option) => option.name === name)?.metadata
      ?.templates?.[language];
    if (seeded !== undefined) update(seeded);
  };

  /**
   * Save the current template into the prompt library.
   *
   * Only offered for a custom prompt whose template is already complete: a
   * library row the API cannot store or a half-written template would just be
   * rejected. The saved prompt then appears in the seeding selects.
   */
  const handleSaveToLibrary = async () => {
    if (!saveName.trim() || missing.length > 0) return;
    setSaving(true);
    try {
      await createRAGPrompt({
        class_name: componentName,
        name: saveName.trim(),
        parameters: { template },
      });
      // This flow always creates a new row, so it must not claim an update.
      enqueueSnackbar(t("generative:rag.prompt.library.created"), {
        variant: "success",
      });
      setSaveName("");
      setSaveOpen(false);
      // Reload the saved prompts so the new row shows up in the selector.
      setLibraryVersion((version) => version + 1);
    } catch (error) {
      console.error("Failed to save prompt to the library:", error);
      enqueueSnackbar(
        getApiErrorMessage(
          error,
          t("generative:rag.prompt.library.createError"),
        ),
        { variant: "error" },
      );
    } finally {
      setSaving(false);
    }
  };

  const canSaveToLibrary = Boolean(
    showSeeding &&
    componentName?.startsWith("Custom") &&
    template.trim() &&
    missing.length === 0,
  );

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
        <Stack direction="row" spacing={1}>
          <TextField
            select
            size="small"
            fullWidth
            label={t("generative:rag.prompt.editor.selectPrompt")}
            value={selection}
            onChange={(event) => handleSelectPrompt(event.target.value)}
          >
            {seeds.length > 0 && (
              <ListSubheader>
                {t("generative:rag.prompt.editor.defaultPrompts")}
              </ListSubheader>
            )}
            {seeds.map((seed) => (
              <MenuItem key={seed.name} value={`default:${seed.name}`}>
                {seed.name}
              </MenuItem>
            ))}
            {savedPrompts.length > 0 && (
              <ListSubheader>
                {t("generative:rag.prompt.editor.savedPrompt")}
              </ListSubheader>
            )}
            {savedPrompts.map((prompt) => (
              <MenuItem key={prompt.id} value={`saved:${prompt.id}`}>
                {prompt.name || `Prompt ${prompt.id}`}
              </MenuItem>
            ))}
          </TextField>
          {selection.startsWith("default:") && (
            <TextField
              select
              size="small"
              label={t("generative:rag.prompt.editor.seedLanguage")}
              value={seedLanguage}
              onChange={(event) => handleLanguageChange(event.target.value)}
              sx={{ minWidth: 96 }}
            >
              {defaultLanguages(selection.slice("default:".length)).map(
                (code) => (
                  <MenuItem key={code} value={code}>
                    {code}
                  </MenuItem>
                ),
              )}
            </TextField>
          )}
        </Stack>
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

      {showSeeding && (
        <Typography variant="caption" color="text.secondary">
          {t("generative:rag.prompt.editor.sessionOnlyHelp")}
        </Typography>
      )}

      {canSaveToLibrary && (
        <Box>
          {saveOpen ? (
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <TextField
                autoFocus
                size="small"
                fullWidth
                label={t("generative:rag.prompt.editor.saveToLibraryName")}
                value={saveName}
                onChange={(event) => setSaveName(event.target.value)}
              />
              <Button
                variant="contained"
                size="small"
                onClick={handleSaveToLibrary}
                disabled={!saveName.trim() || saving}
              >
                {t("generative:rag.prompt.editor.saveToLibrary")}
              </Button>
              <Button size="small" onClick={() => setSaveOpen(false)}>
                {t("common:cancel")}
              </Button>
            </Stack>
          ) : (
            <Button
              variant="outlined"
              size="small"
              onClick={() => {
                setSaveName("");
                setSaveOpen(true);
              }}
            >
              {t("generative:rag.prompt.editor.saveToLibrary")}
            </Button>
          )}
        </Box>
      )}

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
