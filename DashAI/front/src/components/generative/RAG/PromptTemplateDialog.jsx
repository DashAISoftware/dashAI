import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";
import HighlightedTextarea from "./HighlightedTextarea";
import PlaceholdersList from "./PlaceholdersList";
import {
  DEFAULT_PROMPT_LANGUAGE,
  getMissingPromptPlaceholders,
  getPromptPlaceholderDescriptions,
  getPromptRequiredPlaceholders,
  promptTemplateLanguages,
  resolvePromptTemplate,
} from "./promptSchema";

/** The two things the dialog can be doing. */
export const PROMPT_DIALOG_MODES = Object.freeze({
  create: "create",
  edit: "edit",
});

/**
 * Dialog that writes the template of one prompt reference.
 *
 * It edits the template stored in the form's prompt ref, never a prompt
 * library: nothing is loaded from or saved to the prompt database endpoint.
 * The component's built-in templates are only offered through the explicit
 * "load built-in" action, so changing the language alone cannot throw away a
 * template the user is in the middle of writing.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {string}   props.mode - `"create"` or `"edit"`, used for the title.
 * @param {object}   props.component - The prompt component being written for.
 * @param {string}   [props.template] - The template the draft starts from.
 * @param {string}   [props.language] - The language the draft starts from.
 * @param {Function} props.onClose - Closes the dialog without saving.
 * @param {Function} props.onSave - Receives `{template, language}`.
 * @returns {JSX.Element} The prompt template dialog.
 */
export default function PromptTemplateDialog({
  open,
  mode,
  component,
  template,
  language,
  onClose,
  onSave,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const [draft, setDraft] = useState(template ?? "");
  const [draftLanguage, setDraftLanguage] = useState(
    language || DEFAULT_PROMPT_LANGUAGE,
  );
  const textareaRef = useRef(null);

  const availableLanguages = promptTemplateLanguages(component);
  const requiredPlaceholders = getPromptRequiredPlaceholders(component);
  const placeholderDescriptions = getPromptPlaceholderDescriptions(component);
  const missing = getMissingPromptPlaceholders(component, draft);
  const canSave = draft.trim().length > 0 && missing.length === 0;

  // Start from the stored template every time the dialog opens, falling back
  // to the first language the component ships when the stored one is gone.
  useEffect(() => {
    if (!open) return;
    const languages = promptTemplateLanguages(component);
    setDraft(template ?? "");
    setDraftLanguage(
      languages.includes(language)
        ? language
        : languages[0] || DEFAULT_PROMPT_LANGUAGE,
    );
    // Typing changes the draft, not these props, so this only runs on open or
    // when the dialog is pointed at another prompt.
  }, [open, component, template, language]);

  /**
   * Select which language's built-in template the load action would use.
   *
   * The label only: replacing the draft is the explicit load action below, so
   * a language change can never discard what is already written.
   *
   * @param {object} event - The select change event.
   */
  const handleLanguageChange = (event) => {
    setDraftLanguage(event.target.value);
  };

  /** Replace the draft with the chosen language's built-in template. */
  const handleLoadBuiltin = () => {
    setDraft(resolvePromptTemplate(component, {}, draftLanguage));
  };

  /**
   * Insert a placeholder where the caret is, keeping focus in the textarea.
   *
   * The draft is updated functionally so two insertions fired in the same
   * render cannot overwrite each other.
   *
   * @param {string} placeholder - The placeholder token to insert.
   */
  const insertPlaceholder = (placeholder) => {
    const textarea = textareaRef.current;
    if (!textarea) {
      setDraft((prev) => `${prev}${placeholder}`);
      return;
    }
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    setDraft(
      (prev) =>
        `${prev.substring(0, start)}${placeholder}${prev.substring(end)}`,
    );
    requestAnimationFrame(() => {
      const position = start + placeholder.length;
      textarea.selectionStart = position;
      textarea.selectionEnd = position;
      textarea.focus();
    });
  };

  const handleSave = () => onSave({ template: draft, language: draftLanguage });

  const isCreate = mode === PROMPT_DIALOG_MODES.create;
  let title = t("generative:rag.prompt.field.editTitle");
  if (isCreate) title = t("generative:rag.prompt.field.newTitle");

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{ sx: { maxHeight: "80vh", zIndex: 1400 } }}
      BackdropProps={{ sx: { zIndex: 1399 } }}
    >
      <DialogTitle
        sx={{
          bgcolor: "background.paper",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        {title}
        <IconButton
          onClick={onClose}
          size="small"
          sx={{ color: "text.secondary" }}
          aria-label={t("common:close")}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
        <Stack spacing={2}>
          <PlaceholdersList
            required={requiredPlaceholders}
            descriptions={placeholderDescriptions}
            template={draft}
            onInsertPlaceholder={insertPlaceholder}
          />

          <Stack
            direction="row"
            spacing={1}
            alignItems="flex-start"
            useFlexGap
            flexWrap="wrap"
          >
            {availableLanguages.length > 0 && (
              <TextField
                select
                size="small"
                label={t("generative:rag.prompt.editor.seedLanguage")}
                value={draftLanguage}
                onChange={handleLanguageChange}
                helperText={t("generative:rag.prompt.field.languageHelp")}
                sx={{ minWidth: 260 }}
              >
                {availableLanguages.map((code) => (
                  <MenuItem key={code} value={code}>
                    {t(`generative:rag.prompt.languages.${code}`, code)}
                  </MenuItem>
                ))}
              </TextField>
            )}

            <Button
              variant="outlined"
              size="small"
              onClick={handleLoadBuiltin}
              disabled={availableLanguages.length === 0}
              sx={{ mt: 0.5 }}
            >
              {t("generative:rag.prompt.field.loadBuiltin")}
            </Button>
          </Stack>

          <HighlightedTextarea
            ref={textareaRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            minRows={12}
            placeholder={t("generative:rag.prompt.editor.templatePlaceholder")}
          />

          {missing.length > 0 && (
            <Alert severity="error" sx={{ py: 0.5 }}>
              {t("generative:rag.prompt.editor.missingPlaceholder", {
                placeholders: missing.join(", "),
              })}
            </Alert>
          )}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
        <Button onClick={onClose} variant="outlined">
          {t("common:cancel")}
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          color="primary"
          disabled={!canSave}
        >
          {t("common:save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

PromptTemplateDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  mode: PropTypes.oneOf(Object.values(PROMPT_DIALOG_MODES)).isRequired,
  component: PropTypes.object,
  template: PropTypes.string,
  language: PropTypes.string,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
};
