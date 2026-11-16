import axios from "axios";
import api from "./api";
import type {
  InstalledPlugin,
  PluginError,
  PluginPreview,
  PluginSettings,
  PluginUpdates,
  Store,
} from "../types/plugin";

const endpointURL = "/v1/plugin";

const zipForm = (file: Blob, name: string) => {
  const formData = new FormData();
  formData.append("file", file, name);
  return formData;
};

export const getInstalledPlugins = async (): Promise<InstalledPlugin[]> =>
  (await api.get<InstalledPlugin[]>(`${endpointURL}/installed`)).data;

export const getPluginReadme = async (
  pluginId: string,
): Promise<string | null> =>
  (await api.get<string | null>(`${endpointURL}/${pluginId}/readme`)).data;

// What installing this .zip would do. Nothing is installed.
export const previewUpload = async (
  file: Blob,
  name: string,
): Promise<PluginPreview> =>
  (
    await api.post<PluginPreview>(
      `${endpointURL}/upload/validate`,
      zipForm(file, name),
    )
  ).data;

// What installing a release from location (latest or ref) would do
export const previewRemote = async (
  location: string,
  ref?: string | null,
): Promise<PluginPreview> =>
  (
    await api.post<PluginPreview>(`${endpointURL}/validate`, {
      location,
      ref: ref ?? null,
    })
  ).data;

// Installs the very copy the preview reviewed, also the same version
export const installPreview = async (
  preview: string,
): Promise<InstalledPlugin> =>
  (await api.post<InstalledPlugin>(`${endpointURL}/`, { preview })).data;

// A newer release of an installed GitHub plugin, the previewed one.
export const updatePlugin = async (
  pluginId: string,
  preview: string,
): Promise<InstalledPlugin> =>
  (
    await api.post<InstalledPlugin>(`${endpointURL}/${pluginId}/update`, {
      preview,
    })
  ).data;

// Best effort, so the back doesn't keep a dropped preview
export const discardPreview = (preview: string): void => {
  api.delete(`${endpointURL}/previews/${preview}`).catch(() => {});
};

export const uninstallPlugin = async (pluginId: string): Promise<void> => {
  await api.delete(`${endpointURL}/${pluginId}`);
};

// allowBlocked means the user confirmed running a plugin the store retired.
export const setPluginEnabled = async (
  pluginId: string,
  enabled: boolean,
  { allowBlocked = false } = {},
): Promise<InstalledPlugin> =>
  (
    await api.patch<InstalledPlugin>(`${endpointURL}/${pluginId}`, {
      enabled,
      allow_blocked: allowBlocked,
    })
  ).data;

// A plugin's settings form, only while it is active
export const getPluginSettings = async (
  pluginId: string,
): Promise<PluginSettings> =>
  (await api.get<PluginSettings>(`${endpointURL}/${pluginId}/settings`)).data;

// Saves the form, returning the values that differ from the defaults
export const savePluginSettings = async (
  pluginId: string,
  values: Record<string, unknown>,
): Promise<Record<string, unknown>> =>
  (
    await api.put<Pick<PluginSettings, "values">>(
      `${endpointURL}/${pluginId}/settings`,
      { values },
    )
  ).data.values;

// What the last lookup for newer releases found. Never asks GitHub.
export const getPluginUpdates = async (): Promise<PluginUpdates> =>
  (await api.get<PluginUpdates>(`${endpointURL}/updates`)).data;

// Looks for newer releases now ("Check for updates").
export const checkPluginUpdates = async (): Promise<PluginUpdates> =>
  (await api.post<PluginUpdates>(`${endpointURL}/updates/check`)).data;

// The store's index as the backend last read it (never asks GitHub).
export const getStore = async (): Promise<Store> =>
  (await api.get<Store>(`${endpointURL}/store`)).data;

// A store plugin's README at the reviewed commit, null if none
export const getStoreReadme = async (url: string): Promise<string | null> =>
  axios
    .get<string>(url, {
      responseType: "text",
      // Third-party host, never send dashAI's cookies
      withCredentials: false,
    })
    .then(
      ({ data }) => data,
      (error) => {
        if (error.response?.status === 404) return null;
        throw error;
      },
    );

// The coded error of a failed request, else offline or internal_error
export const pluginError = (error: unknown): PluginError => {
  const response = (error as { response?: { data?: { detail?: unknown } } })
    ?.response;
  const detail = response?.data?.detail;
  if (detail && typeof detail === "object" && "code" in detail) {
    return detail as PluginError;
  }
  return {
    code: response ? "internal_error" : "offline",
    detail: typeof detail === "string" ? detail : String(error),
    params: {},
  };
};
