import axios from "axios";
import type { AxiosInstance } from "axios";
import i18n from "i18next";

const api: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
});

api.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  const lang = i18n.language.split("-")[0];
  config.headers["Accept-Language"] = lang;
  return config;
});

export default api;
