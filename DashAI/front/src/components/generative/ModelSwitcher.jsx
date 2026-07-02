import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, MenuItem, Select, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { getRelatedComponents } from "../../api/generativeTask";
import { updateGenerativeSession } from "../../api/session";

/**
 * Session-level model switcher: lets the user change the model used by a
 * generative session, restricted to models of the same task. Models that are
 * download-required but not yet downloaded are shown disabled.
 */
export default function ModelSwitcher({
  sessionId,
  taskName,
  currentModelName,
  onChanged,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const [models, setModels] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!taskName) return;
    getRelatedComponents(taskName)
      .then((components) => setModels(components || []))
      .catch(() => setModels([]));
  }, [taskName]);

  const handleChange = async (event) => {
    const newModel = event.target.value;
    if (!newModel || newModel === currentModelName) return;
    setSaving(true);
    try {
      await updateGenerativeSession({
        id: sessionId,
        formData: { model_name: newModel },
      });
      if (onChanged) onChanged(newModel);
    } catch (error) {
      const status = error?.response?.status;
      enqueueSnackbar(
        status === 409
          ? t("common:componentDownload.mustDownload")
          : t("generative:error.modelSwitchFailed"),
        { variant: "error" },
      );
    } finally {
      setSaving(false);
    }
  };

  // Ensure the current model is always a selectable value even if the list
  // has not loaded yet (avoids an out-of-range MUI Select warning).
  const hasCurrent = models.some((m) => m.name === currentModelName);
  const options = hasCurrent
    ? models
    : [{ name: currentModelName, display_name: currentModelName }, ...models];

  if (!currentModelName) return null;

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {t("generative:label.sessionModel")}
      </Typography>
      <Select
        size="small"
        value={currentModelName}
        onChange={handleChange}
        disabled={saving}
        sx={{ minWidth: 200 }}
      >
        {options.map((model) => {
          const needsDownload =
            Boolean(model.metadata?.requires_download) &&
            !model.downloaded &&
            model.name !== currentModelName;
          return (
            <MenuItem
              key={model.name}
              value={model.name}
              disabled={needsDownload}
            >
              {model.display_name || model.name}
              {needsDownload
                ? ` (${t("generative:label.downloadRequired")})`
                : ""}
            </MenuItem>
          );
        })}
      </Select>
    </Box>
  );
}

ModelSwitcher.propTypes = {
  sessionId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  taskName: PropTypes.string,
  currentModelName: PropTypes.string,
  onChanged: PropTypes.func,
};
