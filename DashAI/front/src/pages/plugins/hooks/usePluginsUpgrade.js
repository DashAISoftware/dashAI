import { upgradePlugin as upgradePluginRequest } from "../../../api/plugins";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

/**
 * custom hook for upgrading a plugin
 * @param {string} pluginId
 * @returns function to upgrade a plugin
 */
export default function usePluginsUpgrade({ pluginId }) {
  const { enqueueSnackbar } = useSnackbar();

  const upgradePlugin = async () => {
    try {
      await upgradePluginRequest(pluginId);
      enqueueSnackbar(t("plugins:message.pluginUpgraded"), {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar(t("plugins:error.upgradingPlugin"), {
        variant: "error",
      });
    }
  };

  return { upgradePlugin };
}
