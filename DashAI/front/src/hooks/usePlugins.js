import { useCallback, useEffect } from "react";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import {
  checkPluginUpdates,
  getInstalledPlugins,
  getPluginUpdates,
  getStore,
  pluginError,
} from "../api/plugins";
import { sharedRead, useSharedRead } from "../utils/sharedRead";

export const PLUGINS_CHANGED = "dashai:plugins-changed";
const announce = () => window.dispatchEvent(new Event(PLUGINS_CHANGED));
// Other dashAI tabs hear it too, a channel never gets its own messages
const otherTabs =
  typeof BroadcastChannel === "undefined"
    ? null
    : new BroadcastChannel(PLUGINS_CHANGED);
if (otherTabs) otherTabs.onmessage = announce;
export const notifyPluginsChanged = () => {
  announce();
  otherTabs?.postMessage(null);
};

export const useOnPluginsChanged = (callback) => {
  useEffect(() => {
    window.addEventListener(PLUGINS_CHANGED, callback);
    return () => window.removeEventListener(PLUGINS_CHANGED, callback);
  }, [callback]);
};

export function useAnnounceInstalled() {
  const { t, i18n } = useTranslation(["plugins"]);
  const { enqueueSnackbar } = useSnackbar();
  return useCallback(
    (plugin, verb, also = []) => {
      notifyPluginsChanged();
      const code = plugin.problem?.code;
      if (code) {
        enqueueSnackbar(
          code === "restart_required"
            ? t("plugins:message.restartRequired", { name: plugin.name })
            : t(`plugins:problem.${code}.title`),
          { variant: "warning" },
        );
        return;
      }
      enqueueSnackbar(
        t(
          `plugins:message.${also.length && verb === "install" ? "installWith" : verb}`,
          {
            name: plugin.name,
            version: `v${plugin.version}`,
            names: new Intl.ListFormat(i18n.language).format(also),
          },
        ),
        { variant: "success" },
      );
    },
    [t, i18n, enqueueSnackbar],
  );
}

const installed = sharedRead({
  read: getInstalledPlugins,
  empty: null,
  refreshOn: PLUGINS_CHANGED,
  revalidate: true, // e.g. a job's worker failed to load one meanwhile
});
export const preloadInstalledPlugins = installed.mounted;
export const freshInstalledPlugins = installed.fresh;

export function useInstalledPlugins() {
  const { data, error } = useSharedRead(installed);
  return {
    plugins: data ?? [],
    loading: data === null && !error,
    error: error && pluginError(error),
  };
}

const POLL_MS = 2500;
const NO_UPDATES = {
  checking: false,
  blocked_changes: 0,
  checked_at: null,
  updates: {},
  errors: {},
  needs_newer_dashai: {},
  store_error: null,
};
let poll = null;
let wasChecking = false;
let seen = null; // blocked_changes as this window's views last read them

const store = sharedRead({
  read: getStore,
  empty: null,
  refreshOn: PLUGINS_CHANGED,
  revalidate: true,
});

const lookedUp = (status) => {
  if (status.blocked_changes !== seen) notifyPluginsChanged();
  else {
    store.refresh();
    installed.refresh();
  }
  seen = status.blocked_changes;
};

const got = (status) => {
  clearTimeout(poll);
  if (status.checking) poll = setTimeout(() => updates.refresh(), POLL_MS);
  else if (wasChecking) lookedUp(status);
  if (seen === null) seen = status.checking ? 0 : status.blocked_changes;
  wasChecking = status.checking;
  return status;
};

const updates = sharedRead({
  read: async () => {
    let status;
    try {
      status = await getPluginUpdates();
    } catch {
      if (wasChecking) poll = setTimeout(() => updates.refresh(), POLL_MS);
      return NO_UPDATES;
    }
    return got(status);
  },
  empty: NO_UPDATES,
  refreshOn: PLUGINS_CHANGED,
  revalidate: true,
});

const check = async () => {
  updates.set({ data: { ...updates.get().data, checking: true } });
  wasChecking = true; // it ends in ``got``, the POST's answer or the read after
  let found = null; // what this lookup found, even if a newer read lands
  const failure = await updates.refresh(async () => {
    found = got(await checkPluginUpdates());
    return found;
  });
  if (failure) await updates.refresh();
  return {
    status: found ?? updates.get().data,
    error: failure && pluginError(failure),
  };
};

export function usePluginUpdates() {
  return { ...useSharedRead(updates).data, check };
}

export function useStore() {
  const { data, error } = useSharedRead(store);
  return {
    store: data,
    loading: data === null && !error,
    error: error && pluginError(error),
  };
}
