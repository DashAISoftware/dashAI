import { updatePlugin as updatePluginRequest } from "../../../api/plugins";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { PluginStatus } from "../../../types/plugin";
import { useTranslation } from "react-i18next";

/**
 * custom hook for updating a plugin status
 * @param {string} pluginId
 * @param {enum} newStatus
 * @param {function} onSuccess
 * @returns function to updatePlugin and loading
 */
export default function usePluginsUpdate({ pluginId, newStatus, onSuccess }) {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(false);
  const { t } = useTranslation(["plugins"]);

  const updatePlugin = async () => {
    try {
      setLoading(true);
      await updatePluginRequest(pluginId, newStatus);

      onSuccess && onSuccess();
      switch (newStatus) {
        case PluginStatus.INSTALLED:
          enqueueSnackbar(t("plugins:message.pluginInstalled"), {
            variant: "success",
          });
          break;
        case PluginStatus.REGISTERED:
          enqueueSnackbar(t("plugins:message.pluginUninstalled"), {
            variant: "success",
          });
          break;
      }
    } catch (error) {
      enqueueSnackbar(t("plugins:error.installingPlugin"), {
        variant: "error",
      });
    }
    setLoading(false);
  };

  return { updatePlugin, loading };
}
