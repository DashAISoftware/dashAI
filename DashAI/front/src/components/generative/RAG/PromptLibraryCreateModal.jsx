import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import PromptEditor from "./PromptEditor";
import { createRAGPrompt } from "../../../api/rag";
import { getChildComponents } from "../../../api/component";
import { getApiErrorMessage } from "../../../utils/apiError";

const FALLBACK_COMPONENT = "CustomRAGGenerationPrompt";

const EMPTY_PROMPT = {
  component: FALLBACK_COMPONENT,
  params: { template: "" },
};

/**
 * Creates a prompt in the library. The template body reuses the same editor
 * a session uses, so placeholders and validation behave identically.
 *
 * @param {object} props
 * @param {boolean} props.open - Whether the dialog is visible.
 * @param {Function} props.onClose - Closes the dialog.
 * @param {Function} props.onCreated - Called with the new prompt id.
 * @param {string} [props.initialTemplate] - Template to preload.
 * @param {string} [props.initialType] - Prompt type to preselect.
 * @param {string} [props.initialSubtype] - Prompt subtype to preselect.
 * @returns {JSX.Element} The create dialog.
 */
export default function PromptLibraryCreateModal({
  open,
  onClose,
  onCreated,
  initialTemplate = "",
  initialType = "",
  initialSubtype = "",
}) {
  const { t } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const [name, setName] = useState("");
  const [promptModel, setPromptModel] = useState(EMPTY_PROMPT);
  const [valid, setValid] = useState(false);
  const [saving, setSaving] = useState(false);
  const [components, setComponents] = useState([]);
  const [loadingComponents, setLoadingComponents] = useState(false);
  const [selectedType, setSelectedType] = useState("");
  const [selectedSubtype, setSelectedSubtype] = useState("");

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    setName("");
    setValid(false);
    setSaving(false);
    setComponents([]);
    setSelectedType("");
    setSelectedSubtype("");
    setLoadingComponents(true);

    getChildComponents("BasePrompt", true)
      .then((list) => {
        if (cancelled) return;
        const custom = list.filter((component) =>
          component.name?.startsWith("Custom"),
        );
        setComponents(custom);
        const preferred =
          custom.find(
            (component) =>
              component.metadata?.type === initialType &&
              (!initialSubtype ||
                component.metadata?.technique === initialSubtype),
          ) ??
          custom.find(
            (component) => component.metadata?.type === initialType,
          ) ??
          custom.find(
            (component) => component.metadata?.type === "generation",
          ) ??
          custom[0];
        if (preferred) {
          setSelectedType(preferred.metadata?.type ?? "");
          setSelectedSubtype(preferred.metadata?.technique ?? "");
          setPromptModel({
            component: preferred.name,
            params: { template: initialTemplate },
          });
        } else {
          setPromptModel({
            ...EMPTY_PROMPT,
            params: { template: initialTemplate },
          });
        }
      })
      .catch((error) => {
        console.error("Failed to load prompt components:", error);
        if (cancelled) return;
        setPromptModel({
          ...EMPTY_PROMPT,
          params: { template: initialTemplate },
        });
      })
      .finally(() => {
        if (!cancelled) setLoadingComponents(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, initialTemplate, initialType, initialSubtype]);

  const typeOptions = useMemo(
    () => [
      ...new Set(
        components.map((component) => component.metadata?.type).filter(Boolean),
      ),
    ],
    [components],
  );

  const subtypeOptions = useMemo(
    () => [
      ...new Set(
        components
          .filter((component) => component.metadata?.type === selectedType)
          .map((component) => component.metadata?.technique)
          .filter(Boolean),
      ),
    ],
    [components, selectedType],
  );

  const selectedComponent = useMemo(() => {
    const candidates = components.filter(
      (component) => component.metadata?.type === selectedType,
    );
    if (subtypeOptions.length > 0) {
      return (
        candidates.find(
          (component) => component.metadata?.technique === selectedSubtype,
        ) ?? candidates[0]
      );
    }
    return candidates[0];
  }, [components, selectedType, selectedSubtype, subtypeOptions.length]);

  const activeComponentName = selectedComponent?.name ?? FALLBACK_COMPONENT;

  const template = promptModel?.params?.template ?? "";
  const canSave = Boolean(
    name.trim() && template.trim() && valid && !saving && !loadingComponents,
  );

  const handleTypeChange = (value) => {
    const candidates = components.filter(
      (component) => component.metadata?.type === value,
    );
    const next = candidates[0];
    setSelectedType(value);
    setSelectedSubtype(next?.metadata?.technique ?? "");
    if (next) {
      setPromptModel({ component: next.name, params: { template: "" } });
    }
  };

  const handleSubtypeChange = (value) => {
    const next = components.find(
      (component) =>
        component.metadata?.type === selectedType &&
        (component.metadata?.technique ?? "") === value,
    );
    setSelectedSubtype(value);
    if (next) {
      setPromptModel({ component: next.name, params: { template: "" } });
    }
  };

  const handleSave = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      const created = await createRAGPrompt({
        class_name: activeComponentName,
        name: name.trim(),
        parameters: { template },
      });
      enqueueSnackbar(t("generative:rag.prompt.library.created"), {
        variant: "success",
      });
      await onCreated?.(created.id);
      onClose();
    } catch (error) {
      console.error("Failed to create prompt:", error);
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
      <DialogTitle>
        {t("generative:rag.prompt.library.createTitle")}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("generative:rag.prompt.library.createSubtitle")}
        </Typography>
        <TextField
          autoFocus
          fullWidth
          required
          label={t("generative:rag.prompt.library.name")}
          value={name}
          onChange={(event) => setName(event.target.value)}
          sx={{ mb: 2 }}
        />
        {loadingComponents ? (
          <CircularProgress size={20} sx={{ display: "block", mb: 2 }} />
        ) : (
          typeOptions.length > 0 && (
            <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
              <TextField
                select
                label={t("generative:rag.prompt.library.filterType")}
                value={selectedType}
                onChange={(event) => handleTypeChange(event.target.value)}
                sx={{ flex: 1, minWidth: 0 }}
              >
                {typeOptions.map((type) => (
                  <MenuItem key={type} value={type}>
                    {t(`generative:rag.prompt.library.types.${type}`, {
                      defaultValue: type,
                    })}
                  </MenuItem>
                ))}
              </TextField>
              {subtypeOptions.length > 0 && (
                <TextField
                  select
                  label={t("generative:rag.prompt.library.filterSubtype")}
                  value={selectedSubtype}
                  onChange={(event) => handleSubtypeChange(event.target.value)}
                  sx={{ flex: 1, minWidth: 0 }}
                >
                  {subtypeOptions.map((subtype) => (
                    <MenuItem key={subtype} value={subtype}>
                      {t(`generative:rag.prompt.library.subtypes.${subtype}`, {
                        defaultValue: subtype,
                      })}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            </Stack>
          )
        )}
        <PromptEditor
          componentName={activeComponentName}
          promptModel={promptModel}
          setPromptModel={setPromptModel}
          onValidityChange={setValid}
          showSeeding={false}
        />
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

PromptLibraryCreateModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onCreated: PropTypes.func,
  initialTemplate: PropTypes.string,
  initialType: PropTypes.string,
  initialSubtype: PropTypes.string,
};
