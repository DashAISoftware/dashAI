import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import PromptEditor from "./PromptEditor";
import { getRAGPrompt, updateRAGPrompt } from "../../../api/rag";
import { getApiErrorMessage } from "../../../utils/apiError";

/**
 * The template of a prompt whichever shape it has.
 *
 * @param {object} prompt - A library prompt.
 * @returns {string} The template text, or an empty string.
 */
function templateOf(prompt) {
  const parameters = prompt?.parameters ?? {};
  if (typeof parameters.template === "string") return parameters.template;
  return Object.values(parameters.templates ?? {})[0] ?? "";
}

/**
 * Read which shape a prompt stores its templates in.
 *
 * A row either holds one explicit `template` or a `templates` map keyed by
 * language, plus the language it resolves to. The editor shows a single text
 * body, so it edits the active language of a map and leaves the other
 * languages untouched.
 *
 * @param {object} prompt - A library prompt.
 * @returns {{usesTemplates: boolean, language: string|null}} The stored shape
 *   and the language the editor writes to.
 */
function templateShape(prompt) {
  const parameters = prompt?.parameters ?? {};
  const explicitTemplate =
    typeof parameters.template === "string" && parameters.template.trim()
      ? parameters.template
      : null;
  const templates = parameters.templates;
  const hasTemplates = Boolean(
    templates &&
    typeof templates === "object" &&
    Object.keys(templates).length > 0,
  );
  if (explicitTemplate || !hasTemplates) {
    return { usesTemplates: false, language: null };
  }
  const languages = Object.keys(templates);
  const stored = parameters.language;
  return {
    usesTemplates: true,
    language: stored && languages.includes(stored) ? stored : languages[0],
  };
}

/**
 * The template the editor starts from.
 *
 * @param {object} prompt - A library prompt.
 * @param {{usesTemplates: boolean, language: string|null}} shape - Its shape.
 * @returns {string} The template text to edit, or an empty string.
 */
function editableTemplate(prompt, shape) {
  if (!shape.usesTemplates) return templateOf(prompt);
  return prompt?.parameters?.templates?.[shape.language] ?? "";
}

/**
 * Edits a library prompt in place. The component (class_name) is fixed: the
 * API can only edit the row it owns, so switching class would silently create
 * a different prompt. The template body reuses the session editor.
 *
 * @param {object} props
 * @param {boolean} props.open - Whether the dialog is visible.
 * @param {Function} props.onClose - Closes the dialog.
 * @param {number|null} props.promptId - The library prompt to edit.
 * @param {Function} [props.onSaved] - Called with the prompt id after saving.
 * @returns {JSX.Element} The edit dialog.
 */
export default function PromptLibraryEditModal({
  open,
  onClose,
  promptId,
  onSaved,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const [loading, setLoading] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [loadVersion, setLoadVersion] = useState(0);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState(null);
  const [shape, setShape] = useState({
    usesTemplates: false,
    language: null,
  });
  const [promptModel, setPromptModel] = useState(null);
  const [valid, setValid] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open || promptId == null) return undefined;
    let cancelled = false;
    setLoading(true);
    setLoadFailed(false);
    setSaving(false);
    setName("");
    setPrompt(null);
    setShape({ usesTemplates: false, language: null });
    setPromptModel(null);
    setValid(false);

    getRAGPrompt(promptId)
      .then((loaded) => {
        if (cancelled) return;
        const loadedShape = templateShape(loaded);
        setPrompt(loaded);
        setName(loaded.name ?? "");
        setShape(loadedShape);
        setPromptModel({
          component: loaded.class_name,
          params: { template: editableTemplate(loaded, loadedShape) },
        });
      })
      .catch((error) => {
        console.error("Failed to load prompt:", error);
        if (cancelled) return;
        setLoadFailed(true);
        enqueueSnackbar(
          getApiErrorMessage(
            error,
            t("generative:rag.prompt.library.loadError"),
          ),
          { variant: "error" },
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, promptId, loadVersion, enqueueSnackbar, t]);

  const componentName = prompt?.class_name ?? "";

  const typeChip = useMemo(() => {
    if (!prompt?.prompt_type) return null;
    return t(`generative:rag.prompt.library.types.${prompt.prompt_type}`, {
      defaultValue: prompt.prompt_type,
    });
  }, [prompt, t]);

  const languageLabel = useMemo(() => {
    if (!shape.usesTemplates || !shape.language) return null;
    return t(`generative:rag.prompt.languages.${shape.language}`, {
      defaultValue: shape.language,
    });
  }, [shape, t]);

  const template = promptModel?.params?.template ?? "";
  const canSave = Boolean(
    prompt && name.trim() && template.trim() && valid && !saving && !loading,
  );

  /**
   * The parameters to send, in the shape the prompt already stores.
   *
   * Sending a bare `{template}` to a multi-language prompt would replace the
   * map and drop every other language, so a map is rebuilt with only the
   * edited language replaced.
   *
   * @returns {object} The parameters for the PATCH request.
   */
  const parametersToSave = () => {
    if (!shape.usesTemplates) return { template };
    const stored = prompt?.parameters ?? {};
    const storedTemplates = stored.templates ?? {};
    const rest = { ...stored };
    delete rest.template;
    delete rest.templates;
    return {
      ...rest,
      templates: { ...storedTemplates, [shape.language]: template },
    };
  };

  const handleSave = async () => {
    if (!canSave || promptId == null) return;
    setSaving(true);
    try {
      await updateRAGPrompt(promptId, {
        name: name.trim(),
        parameters: parametersToSave(),
      });
      enqueueSnackbar(t("generative:rag.prompt.library.saved"), {
        variant: "success",
      });
      await onSaved?.(promptId);
      onClose();
    } catch (error) {
      console.error("Failed to update prompt:", error);
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

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>{t("generative:rag.prompt.library.editTitle")}</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("generative:rag.prompt.library.editSubtitle")}
        </Typography>

        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        ) : loadFailed ? (
          <Alert
            severity="error"
            action={
              <Button
                color="inherit"
                size="small"
                onClick={() => setLoadVersion((version) => version + 1)}
              >
                {t("generative:rag.prompt.library.retry")}
              </Button>
            }
          >
            {t("generative:rag.prompt.library.loadError")}
          </Alert>
        ) : (
          <>
            <TextField
              autoFocus
              fullWidth
              required
              label={t("generative:rag.prompt.library.name")}
              value={name}
              onChange={(event) => setName(event.target.value)}
              sx={{ mb: 2 }}
            />
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              useFlexGap
              sx={{ mb: 2, flexWrap: "wrap" }}
            >
              {typeChip && (
                <Chip
                  size="small"
                  color="info"
                  variant="outlined"
                  label={typeChip}
                />
              )}
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontFamily: theme.typography.code.fontFamily }}
              >
                {componentName}
              </Typography>
            </Stack>
            {languageLabel && (
              <Typography
                variant="caption"
                display="block"
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                {t("generative:rag.prompt.library.editLanguage", {
                  language: languageLabel,
                })}
              </Typography>
            )}
            {promptModel && (
              <PromptEditor
                componentName={componentName}
                promptModel={promptModel}
                setPromptModel={setPromptModel}
                onValidityChange={setValid}
                showSeeding={false}
              />
            )}
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose}>{t("common:cancel")}</Button>
        <Button variant="contained" onClick={handleSave} disabled={!canSave}>
          {t("generative:rag.prompt.library.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

PromptLibraryEditModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  promptId: PropTypes.number,
  onSaved: PropTypes.func,
};
