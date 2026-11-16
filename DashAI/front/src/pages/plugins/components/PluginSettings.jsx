import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Alert, AlertTitle, Box, Button, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import FormSchema from "../../../components/shared/FormSchema";
import FormSchemaContainer from "../../../components/shared/FormSchemaContainer";
import { useFormSchemaStore } from "../../../contexts/schema";
import {
  getPluginSettings,
  pluginError,
  savePluginSettings,
} from "../../../api/plugins";
import { formattedModel, generateYupSchema } from "../../../utils/schema";
import { errorMessage } from "../pluginUtils";

// The formatted schema and the saved values over its defaults
const formOf = async ({ schema, values }) => {
  const formatted = await formattedModel(schema);
  return {
    schema: formatted,
    values: { ...generateYupSchema(formatted).initialValues, ...values },
  };
};

function SettingsForm({ plugin, settings, onStale }) {
  const { t } = useTranslation(["plugins"]);
  const { enqueueSnackbar } = useSnackbar();
  const { formValues } = useFormSchemaStore();
  // Saved values as JSON, as a sub-form edits the store's objects in place
  const [saved, setSaved] = useState(null);
  const [error, setError] = useState(false);
  const [saving, setSaving] = useState(false);

  const current = JSON.stringify(formValues);
  const seeded = Object.keys(formValues).length > 0;
  useEffect(() => {
    if (saved === null && seeded) setSaved(current);
  }, [saved, seeded, current]);
  const dirty = saved !== null && current !== saved;

  const save = async () => {
    setSaving(true);
    try {
      await savePluginSettings(plugin.id, formValues);
      setSaved(current);
      enqueueSnackbar(t("plugins:settings.saved", { name: plugin.name }), {
        variant: "success",
      });
    } catch (failure) {
      const coded = pluginError(failure);
      enqueueSnackbar(errorMessage(t, coded), { variant: "error" });
      if (coded.code === "invalid_settings") onStale();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box
      data-tour="plugin-settings-form"
      sx={{ display: "flex", flexDirection: "column", gap: 2 }}
    >
      <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
        {t("plugins:settings.intro")}
      </Typography>
      <FormSchema
        formattedSchema={settings.schema}
        initialValues={settings.values}
        setError={setError}
        hideButtons
      />
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 2,
        }}
      >
        {dirty && (
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            {t("plugins:settings.unsaved")}
          </Typography>
        )}
        <Button
          variant="contained"
          onClick={save}
          disabled={!dirty || error || saving}
        >
          {t("plugins:settings.save")}
        </Button>
      </Box>
    </Box>
  );
}
SettingsForm.propTypes = {
  plugin: PropTypes.object.isRequired,
  settings: PropTypes.object.isRequired,
  onStale: PropTypes.func.isRequired,
};

export default function PluginSettings({ plugin, shown }) {
  const { t } = useTranslation(["plugins"]);
  const [settings, setSettings] = useState(null);
  const [failure, setFailure] = useState(null);
  const [reads, setReads] = useState(0);
  // Values, so a reread of the list doesn't wipe what is being typed
  const { id, active, version, ref, updated_at: modified } = plugin;

  useEffect(() => {
    setSettings(null);
    setFailure(null);
    if (!active) return undefined;
    let cancelled = false;
    getPluginSettings(id)
      .then(formOf)
      .then((read) => {
        if (!cancelled) setSettings(read);
      })
      .catch((error) => {
        if (!cancelled) setFailure(errorMessage(t, pluginError(error)));
      });
    return () => {
      cancelled = true;
    };
    // t, as the schema comes in the user's language.
  }, [id, active, version, ref, modified, reads, t]);

  let content = null;
  if (!active) {
    const why = plugin.problem ? "problem" : "inactive";
    content = (
      <Alert severity="info" variant="outlined">
        <AlertTitle>{t(`plugins:settings.${why}Title`)}</AlertTitle>
        {t(`plugins:settings.${why}Text`)}
      </Alert>
    );
  } else if (failure) {
    content = (
      <Alert severity="error" variant="outlined">
        {failure}
      </Alert>
    );
  } else if (settings) {
    content = (
      <FormSchemaContainer>
        <SettingsForm
          plugin={plugin}
          settings={settings}
          onStale={() => setReads((n) => n + 1)}
        />
      </FormSchemaContainer>
    );
  }
  return <Box hidden={!shown}>{content}</Box>;
}
PluginSettings.propTypes = {
  plugin: PropTypes.object.isRequired,
  shown: PropTypes.bool.isRequired,
};
