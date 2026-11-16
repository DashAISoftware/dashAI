import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import { useTranslation } from "react-i18next";
import FormSchemaFieldCard from "../../shared/FormSchemaFieldCard";
import { renderTemplateWithHighlights } from "../../../pages/generative/RAGSession/components/sectionUtils";
import PromptTemplateDialog, {
  PROMPT_DIALOG_MODES,
} from "./PromptTemplateDialog";
import usePromptOptions from "./usePromptOptions";
import { getLibraryPrompts } from "../../../api/rag";
import {
  DEFAULT_PROMPT_LANGUAGE,
  PROMPT_LANGUAGE_PARAM,
  PROMPT_TEMPLATE_PARAM,
  buildPromptRef,
  getMissingPromptPlaceholders,
  getPromptDisplayName,
  isDefaultPromptComponent,
  promptTemplateLanguages,
  readPromptSelection,
  resolvePromptTemplate,
} from "./promptSchema";

/** Width the selector keeps before it starts wrapping the action row. */
const SELECTOR_MIN_WIDTH = 220;

/**
 * Template text stored in a prompt's parameters.
 *
 * Saved prompts may store a single `template` or a `templates` map; the
 * explicit text wins, then the requested language, then any stored language.
 *
 * @param {object} parameters - The prompt's stored parameters.
 * @param {string} language - The language to prefer.
 * @returns {string} The template, or an empty string.
 */
function templateFromParameters(parameters, language) {
  const stored = parameters ?? {};
  if (typeof stored.template === "string" && stored.template.trim()) {
    return stored.template;
  }
  const templates = stored.templates ?? {};
  return (
    templates[language] ??
    templates[DEFAULT_PROMPT_LANGUAGE] ??
    Object.values(templates).find(
      (value) => typeof value === "string" && value.trim(),
    ) ??
    ""
  );
}

/**
 * Whether two prompt parameter objects carry the same values.
 *
 * @param {object} left - First parameters object.
 * @param {object} right - Second parameters object.
 * @returns {boolean} True when their serialized values match.
 */
function sameParameters(left, right) {
  return JSON.stringify(left ?? {}) === JSON.stringify(right ?? {});
}

/**
 * A short discriminator for two saved prompts that share a name.
 *
 * @param {object} prompt - A library prompt.
 * @returns {string} The prompt's subtype, type or class, plus its id.
 */
function libraryPromptKind(prompt) {
  const kind = prompt?.prompt_subtype || prompt?.prompt_type;
  return kind ? `${kind} #${prompt.id}` : `#${prompt.id}`;
}

/**
 * Schema card for a prompt-typed field.
 *
 * Renders the selected prompt, the template it resolves to and the two ways to
 * change it: pick another registered prompt, or write the template of the
 * current/custom one. The selection is never copied into local state — the
 * field value is the single source of truth — so the card stays controlled and
 * the dialog only ever emits the canonical `{component, params}` reference.
 *
 * @param {object}   props
 * @param {string}   props.name - Field name in the parent form.
 * @param {object}   props.paramJsonSchema - The prompt field's schema.
 * @param {object}   props.field - Formik field state (`value`, `error`,
 *   `onChange`).
 * @param {string}   [props.description] - Description to show, already merged
 *   with a rule reason by the caller.
 * @param {boolean}  [props.disabled] - Disables the selector and both actions.
 * @param {Function} [props.promptFilter] - `(fieldName, option) => boolean`
 *   deciding which prompt components are offered.
 * @returns {JSX.Element} The prompt card and its template dialog.
 */
export default function PromptFieldCard({
  name,
  paramJsonSchema,
  field,
  description,
  disabled = false,
  promptFilter,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const theme = useTheme();
  const [dialog, setDialog] = useState(null);

  const {
    options,
    loading,
    error: loadError,
  } = usePromptOptions(paramJsonSchema.parent);

  // Filtering happens here, not in the loader: the loaded list is also what
  // lets a stored prompt stay readable when this technique no longer offers it.
  const stageOptions = useMemo(
    () =>
      options.filter((option) => !promptFilter || promptFilter(name, option)),
    [options, name, promptFilter],
  );

  // The schema's `language` parameter identifies a concrete default prompt.
  // Generic custom classes keep the base template-only schema and are only a
  // container for a user-written template, so they do not populate the
  // selector. The New prompt action creates one instead.
  const selectableOptions = useMemo(
    () => stageOptions.filter(isDefaultPromptComponent),
    [stageOptions],
  );

  // Saved library prompts are offered next to the registered components so a
  // user can reuse a shared prompt without retyping its template. They are
  // bound by content: the ref carries the saved prompt's own class and
  // parameters, which the backend resolves back to the library row.
  const [libraryPrompts, setLibraryPrompts] = useState([]);
  useEffect(() => {
    let cancelled = false;
    getLibraryPrompts()
      .then((prompts) => {
        if (!cancelled) setLibraryPrompts(prompts ?? []);
      })
      .catch((error) => {
        console.error("Failed to load saved prompts:", error);
        if (!cancelled) setLibraryPrompts([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The stage's registered components are the only prompts this slot can run,
  // and a saved prompt is bound by its own class: a row whose class is not
  // offered here could never be resolved, so it is not offered either.
  const libraryOptions = useMemo(() => {
    if (libraryPrompts.length === 0 || stageOptions.length === 0) return [];

    const compatible = libraryPrompts.filter(
      (prompt) =>
        prompt?.is_library &&
        stageOptions.some((option) => option.name === prompt.class_name),
    );

    // Two rows can share a name; the selector has to tell them apart.
    const nameCounts = compatible.reduce((counts, prompt) => {
      counts.set(prompt.name, (counts.get(prompt.name) ?? 0) + 1);
      return counts;
    }, new Map());

    const options = [];
    compatible.forEach((prompt) => {
      const base = stageOptions.find(
        (option) => option.name === prompt.class_name,
      );
      if (!base) return;
      const label = prompt.name || base.metadata?.name || base.name;
      const repeated = (nameCounts.get(prompt.name) ?? 0) > 1;
      const displayLabel = repeated
        ? `${label} — ${libraryPromptKind(prompt)}`
        : label;
      options.push({
        ...base,
        // A synthetic name keeps two saved prompts of the same component
        // distinct inside the Autocomplete; the real class is carried
        // separately so the emitted ref stays canonical.
        name: `${base.name}#library-${prompt.id}`,
        // Custom components label themselves from metadata, so the saved
        // name has to override it for the option to read as the user's row.
        metadata: {
          ...base.metadata,
          name: displayLabel,
        },
        libraryPromptId: prompt.id,
        libraryClassName: prompt.class_name,
        libraryParameters: prompt.parameters ?? {},
        display_name: displayLabel,
      });
    });
    return options;
  }, [libraryPrompts, stageOptions]);

  const selection = readPromptSelection(field.value);
  const selectedComponent = useMemo(() => {
    const registered = options.find(
      (option) => option.name === selection.component,
    );
    if (registered) return registered;
    // The stored component may have been unregistered since the session was
    // saved; a minimal stand-in keeps the value shown and editable instead of
    // silently reading as "nothing selected".
    if (!selection.component) return null;
    return {
      name: selection.component,
      display_name: selection.component,
      metadata: {},
    };
  }, [options, selection.component]);

  // A saved prompt is selected when the form already holds its exact class and
  // parameters. Anything else (an edit, a default, a custom ref) falls back to
  // the registered component as before.
  const libraryMatch = useMemo(() => {
    if (!selection.component) return null;
    return (
      libraryOptions.find(
        (option) =>
          option.libraryClassName === selection.component &&
          sameParameters(option.libraryParameters, selection.params),
      ) ?? null
    );
  }, [libraryOptions, selection.component, selection.params]);

  const activeOption = libraryMatch ?? selectedComponent;

  // The current selection is always an option, even when the filter rejects it,
  // or the Autocomplete cannot render the value it is given.
  const autocompleteOptions = useMemo(() => {
    const list = [...libraryOptions, ...selectableOptions];
    if (
      activeOption &&
      !list.some((option) => option.name === activeOption.name)
    ) {
      list.unshift(activeOption);
    }
    return list;
  }, [libraryOptions, selectableOptions, activeOption]);

  const language =
    selection.params?.[PROMPT_LANGUAGE_PARAM] || DEFAULT_PROMPT_LANGUAGE;
  const template = libraryMatch
    ? templateFromParameters(libraryMatch.libraryParameters, language) ||
      resolvePromptTemplate(activeOption, {}, language)
    : resolvePromptTemplate(selectedComponent, selection.params, language);
  const missing = getMissingPromptPlaceholders(activeOption, template);
  // Only a technique's own prompts may be created: offering the custom prompt
  // here would let a user write a template this stage never runs.
  const customOption = useMemo(
    () =>
      stageOptions.find((option) => !isDefaultPromptComponent(option)) ?? null,
    [stageOptions],
  );

  const errorMessage =
    typeof field.error === "string" ? field.error : field.error?.message;

  /**
   * Write a canonical prompt reference back to the form.
   *
   * @param {string} component - The prompt component name.
   * @param {object} params - The params to store for it.
   */
  const emit = (component, params) =>
    field.onChange(buildPromptRef(component, params));

  /**
   * Switch to another registered prompt component.
   *
   * A component that ships built-in templates stores the language alone: the
   * template is resolved from the component at render time, so the form keeps
   * following the language instead of freezing one translation into the ref. A
   * component without templates can only store text the user wrote, so the ref
   * is written once that text exists and satisfies the placeholders; anything
   * else opens the dialog, and cancelling it leaves the previous ref intact.
   *
   * @param {object} _event - The autocomplete event.
   * @param {object|null} option - The selected prompt component.
   */
  const handleSelect = (_event, option) => {
    if (!option) return;

    // A saved library prompt is bound by content: the emitted ref carries the
    // row's own class and parameters, and its template is already complete.
    if (option.libraryPromptId) {
      emit(option.libraryClassName, option.libraryParameters ?? {});
      return;
    }

    const languages = promptTemplateLanguages(option);
    if (languages.length > 0) {
      let nextLanguage = languages[0];
      if (languages.includes(language)) {
        nextLanguage = language;
      } else if (languages.includes(DEFAULT_PROMPT_LANGUAGE)) {
        nextLanguage = DEFAULT_PROMPT_LANGUAGE;
      }
      emit(option.name, { [PROMPT_LANGUAGE_PARAM]: nextLanguage });
      return;
    }

    const isUsable =
      template && getMissingPromptPlaceholders(option, template).length === 0;
    if (isUsable) {
      emit(option.name, { [PROMPT_TEMPLATE_PARAM]: template });
      return;
    }

    // Nothing valid to persist yet: ask for the template first, and only store
    // it on save. The current text is kept as a starting point so a rejected
    // template stays visible and fixable.
    setDialog({
      mode:
        option.name === selection.component
          ? PROMPT_DIALOG_MODES.edit
          : PROMPT_DIALOG_MODES.create,
      component: option,
      template,
      language,
    });
  };

  /** Open the dialog to write a template under the custom component. */
  const handleNew = () => {
    if (!customOption) return;
    setDialog({
      mode: PROMPT_DIALOG_MODES.create,
      component: customOption,
      template,
      language,
    });
  };

  /** Open the dialog to rewrite the current component's template. */
  const handleEdit = () => {
    // Editing a saved prompt here is a session-local edit: the ref keeps the
    // saved class but its new parameters make the backend bind a draft copy.
    const editOption = libraryMatch
      ? { ...libraryMatch, name: libraryMatch.libraryClassName }
      : selectedComponent;
    if (!editOption) return;
    setDialog({
      mode: PROMPT_DIALOG_MODES.edit,
      component: editOption,
      template,
      language,
    });
  };

  /**
   * Store the template written in the dialog.
   *
   * Writing for the component the form already holds keeps every other param
   * the reference carried; picking a different (template-less) component starts
   * from a clean ref. The language is stored only for components that actually
   * ship templates, so no dead param is written onto a custom prompt.
   *
   * @param {object} saved - `{template, language}` from the dialog.
   */
  const handleDialogSave = ({ template: savedTemplate, language: saved }) => {
    if (!dialog) return;
    const supportsLanguages =
      promptTemplateLanguages(dialog.component).length > 0;
    const params =
      dialog.component.name === selection.component
        ? { ...selection.params }
        : {};
    const builtinTemplate = supportsLanguages
      ? resolvePromptTemplate(dialog.component, {}, saved)
      : "";
    // A built-in template that was only previewed and saved unchanged stays
    // language-driven: pinning it into the ref would freeze the translation and
    // defeat the reason the selection stores the language alone.
    if (!supportsLanguages || savedTemplate !== builtinTemplate) {
      params[PROMPT_TEMPLATE_PARAM] = savedTemplate;
    } else {
      delete params[PROMPT_TEMPLATE_PARAM];
    }
    if (supportsLanguages) params[PROMPT_LANGUAGE_PARAM] = saved;
    emit(dialog.component.name, params);
    setDialog(null);
  };

  return (
    <>
      <FormSchemaFieldCard
        label={paramJsonSchema.title}
        paramKey={name}
        description={description ?? paramJsonSchema.description}
        errorMessage={errorMessage}
      >
        <Stack spacing={2}>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            useFlexGap
            flexWrap="wrap"
          >
            <Autocomplete
              size="small"
              options={autocompleteOptions}
              loading={loading}
              disabled={disabled}
              disableClearable
              value={activeOption}
              getOptionLabel={getPromptDisplayName}
              isOptionEqualToValue={(option, value) =>
                option?.name === value?.name
              }
              // The stored value is prepended even when the technique filter
              // rejects it, so it stays readable; it must not be re-selectable
              // as a valid option for this stage. Saved prompts are always
              // valid choices for their own type.
              getOptionDisabled={(option) =>
                !option.libraryPromptId && !selectableOptions.includes(option)
              }
              onChange={handleSelect}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={t("generative:rag.prompt.field.select")}
                  placeholder={t("generative:rag.prompt.field.select")}
                />
              )}
              sx={{ flex: 1, minWidth: SELECTOR_MIN_WIDTH }}
            />

            <Tooltip title={t("generative:rag.prompt.field.new")}>
              <span>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<AddIcon />}
                  disabled={disabled || !customOption}
                  onClick={handleNew}
                >
                  {t("generative:rag.prompt.field.new")}
                </Button>
              </span>
            </Tooltip>
          </Stack>

          {libraryOptions.length > 0 && (
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              useFlexGap
              flexWrap="wrap"
            >
              <Chip
                size="small"
                color="info"
                variant="outlined"
                label={t("generative:rag.prompt.field.saved")}
              />
              <Typography variant="caption" color="text.secondary">
                {t("generative:rag.prompt.field.savedHelp")}
              </Typography>
            </Stack>
          )}

          {loadError && (
            <Alert severity="warning" sx={{ py: 0.5 }}>
              {t("generative:rag.prompt.field.loadError")}
            </Alert>
          )}

          <Box
            sx={{
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              bgcolor: "background.box",
              px: 2,
              py: 1.5,
              fontFamily: theme.typography.code.fontFamily,
              fontSize: theme.typography.body2.fontSize,
              lineHeight: 1.6,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              maxHeight: 220,
              overflowY: "auto",
              overscrollBehavior: "contain",
            }}
          >
            {template ? (
              renderTemplateWithHighlights(
                template,
                {
                  bg: theme.palette.placeholder.bg,
                  text: theme.palette.placeholder.text,
                },
                theme.typography.code.fontFamily,
              )
            ) : (
              <Typography variant="body2" color="text.secondary">
                {t("generative:rag.prompt.field.empty")}
              </Typography>
            )}
          </Box>

          {missing.length > 0 && (
            <Alert severity="warning" sx={{ py: 0.5 }}>
              {t("generative:rag.prompt.editor.missingPlaceholder", {
                placeholders: missing.join(", "),
              })}
            </Alert>
          )}

          <Box>
            <Button
              variant="text"
              size="small"
              startIcon={<EditIcon />}
              disabled={disabled || !activeOption}
              onClick={handleEdit}
            >
              {t("generative:rag.prompt.field.edit")}
            </Button>
            <Typography
              variant="caption"
              display="block"
              color="text.secondary"
              sx={{ mt: 0.5 }}
            >
              {t("generative:rag.prompt.field.sessionOnlyHelp")}
            </Typography>
          </Box>
        </Stack>
      </FormSchemaFieldCard>

      {dialog && (
        <PromptTemplateDialog
          open
          mode={dialog.mode}
          component={dialog.component}
          template={dialog.template}
          language={dialog.language}
          onClose={() => setDialog(null)}
          onSave={handleDialogSave}
        />
      )}
    </>
  );
}

PromptFieldCard.propTypes = {
  name: PropTypes.string.isRequired,
  paramJsonSchema: PropTypes.object.isRequired,
  field: PropTypes.shape({
    value: PropTypes.any,
    onChange: PropTypes.func.isRequired,
    error: PropTypes.any,
  }).isRequired,
  description: PropTypes.string,
  disabled: PropTypes.bool,
  promptFilter: PropTypes.func,
};
