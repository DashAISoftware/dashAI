import axios from "axios";
import type { AxiosInstance } from "axios";
import i18n from "../utils/i18n";

const api: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
  // Sends the session cookie when the dev server (port 3000) calls the API
  // on port 8000; same-origin requests send it anyway
  withCredentials: true,
  paramsSerializer: (params) => {
    const sp = new URLSearchParams();
    for (const [key, val] of Object.entries(params)) {
      if (Array.isArray(val)) {
        val.forEach((v) => sp.append(key, String(v)));
      } else if (val !== null && val !== undefined) {
        sp.append(key, String(val));
      }
    }
    return sp.toString();
  },
});

api.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  const lang = (i18n as any).language.split("-")[0];
  config.headers["Accept-Language"] = lang;
  return config;
});

export default api;
