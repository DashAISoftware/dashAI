/**
 * Format a byte count for people, as "1.5 MB".
 *
 * @param {number} bytes - The size in bytes.
 * @returns {string} The size with one decimal and its unit.
 */
export function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

/**
 * The .dashai file name of a session. Mirrors session_filename in the
 * backend so the download keeps its name.
 *
 * @param {string} name - The session name.
 * @returns {string} A safe file name ending in .dashai.
 */
export function sessionFilename(name) {
  const base = (name || "").replace(/[^A-Za-z0-9_-]+/g, "_");
  return `${base.replace(/^_+|_+$/g, "") || "session"}.dashai`;
}
