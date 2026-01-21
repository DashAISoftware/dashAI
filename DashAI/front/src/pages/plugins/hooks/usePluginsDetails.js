import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import { getPluginById as getPluginDetailsRequest } from "../../../api/plugins";
import { useTranslation } from "react-i18next";

/**
 * custom hook to get plugin from the backend using the id
 * @param {string} pluginId
 * @param {boolean} updatePluginFlag
 * @param {function} setUpdatePluginFlag
 * @returns plugin searched by id, loading, error
 */
export default function usePluginsDetails({
  pluginId,
  updatePluginFlag,
  setUpdatePluginFlag,
}) {
  const [loading, setLoading] = useState(true);
  const [plugin, setPlugin] = useState([]);
  const { enqueueSnackbar } = useSnackbar();
  const [error, setError] = useState(false);
  const { t } = useTranslation(["plugins"]);

  const getPluginsDetails = async () => {
    setLoading(true);
    try {
      const plugin = await getPluginDetailsRequest(pluginId);
      setPlugin(plugin);
    } catch (error) {
      enqueueSnackbar(t("plugins:error.obtainPluginDetails"), {
        variant: "error",
      });
      setError(true);
    } finally {
      setLoading(false);
      setUpdatePluginFlag(false);
    }
  };

  useEffect(() => {
    if (updatePluginFlag) {
      getPluginsDetails();
    }
  }, [pluginId, updatePluginFlag]);

  return { plugin, loading, error };
}
