const API_BASE = import.meta.env.VITE_API_URL || "";
const API_ORIGIN = (() => {
  try {
    return new URL(API_BASE).origin;
  } catch {
    return "";
  }
})();

export const normalizeUrl = (url) => {
  if (!url) return url;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_ORIGIN}${url}`;
};
