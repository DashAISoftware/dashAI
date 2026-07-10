/**
 * Shared language constants used across RAG prompt components.
 */
export const LANGUAGE_OPTIONS = [
  { code: "en", name: "English" },
  { code: "es", name: "Español" },
  { code: "pt", name: "Português" },
];

export const LANGUAGE_NAME_MAP = Object.fromEntries(
  LANGUAGE_OPTIONS.map((opt) => [opt.code, opt.name]),
);
