import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import { getPlugins as getPluginsRequest } from "../../../api/plugins";
import { PluginStatus } from "../../../types/plugin";
import { useTranslation } from "react-i18next";

/**
 * Custom hook to get plugins from the backend
 * @param {function} onSettled
 * @param {boolean} refresh
 * @returns pluginsBrowse, pluginsInstalled, loading
 */
export default function usePlugins({ onSettled, refresh = false }) {
  const [loading, setLoading] = useState(true);
  const [pluginsBrowse, setPluginsBrowse] = useState([]);
  const [pluginsInstalled, setPluginsInstalled] = useState([]);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["plugins"]);

  const getPlugins = async () => {
    try {
      const plugins = await getPluginsRequest();
      setPluginsBrowse(
        plugins.filter((plugin) =>
          [PluginStatus.REGISTERED].includes(plugin.status),
        ),
      );
      setPluginsInstalled(
        plugins.filter((plugin) =>
          [PluginStatus.INSTALLED].includes(plugin.status),
        ),
      );
    } catch (error) {
      enqueueSnackbar(t("plugins:error.obtainPlugins"), {
        variant: "error",
      });
    } finally {
      onSettled && onSettled();
      setLoading(false);
    }
  };

  useEffect(() => {
    if (refresh) {
      setLoading(true);
      getPlugins();
    }
  }, [refresh]);

  return { pluginsBrowse, pluginsInstalled, loading };
}
