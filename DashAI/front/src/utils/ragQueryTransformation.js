/**
 * Pure helpers shared by the query transformation picker and its advanced
 * modal.
 *
 * They live here rather than in either component so the picker and the modal
 * can both use them without importing each other: the picker renders the modal,
 * so a modal-to-picker import closes a cycle.
 */

import i18next from "i18next";

/**
 * Reads the `llm_model` placeholder a transformer's schema declares.
 *
 * All transformation techniques share their schema, so the first component
 * carrying the placeholder carries the backend-declared default generator.
 *
 * @param {Array} transformers - The transformation components from the API.
 * @returns {string|null} The default generator name, or null when no schema
 *   declares one.
 */
export function resolveDefaultGeneratorName(transformers) {
  const declaring = (transformers || []).find(
    (component) =>
      component.schema?.properties?.llm_model?.placeholder?.component,
  );
  return declaring?.schema.properties.llm_model.placeholder.component ?? null;
}

/**
 * Picks the language model a freshly enabled stage is seeded with.
 *
 * Query transformation needs a downloaded model. The backend-declared default
 * is preferred when it is downloaded, otherwise the first downloaded model.
 * Returns null when nothing is downloaded: the caller must refuse to enable
 * the stage rather than seed a model the backend would reject with a 409.
 *
 * @param {Array} generators - The generator components from the API.
 * @param {string|null} defaultName - The backend-declared default generator.
 * @returns {object|null} The generator to seed, or null when none qualifies.
 */
export function resolveEnableGenerator(generators, defaultName) {
  const downloaded = (generators || []).filter(
    (generator) => generator.downloaded,
  );
  return (
    downloaded.find((generator) => generator.name === defaultName) ??
    downloaded[0] ??
    null
  );
}

/**
 * Whether a stage ref carries the two references the backend requires on save:
 * the transformation LLM (`llm_model`) and the prompt.
 * @param {object|null} ref - The `{component, params}` stage ref.
 * @returns {boolean} True when both references name a component.
 */
export function isCompleteQueryTransformationRef(ref) {
  return Boolean(
    ref?.params?.llm_model?.component && ref?.params?.prompt?.component,
  );
}

/**
 * Resolves a component's display name or description, whether the API shipped
 * it as a localized string or as a multilingual object (legacy endpoints may
 * emit the raw object shape).
 *
 * A multilingual object is read in the interface language first, then English,
 * then Spanish, then its first string.
 *
 * @param {string|object|undefined} value - The multilingual or plain value.
 * @param {string} fallback - What to return when nothing resolvable is there.
 * @param {string} [language] - The language to prefer; defaults to the active
 *   i18next language.
 * @returns {string} A renderable plain string.
 */
export function resolveLabel(
  value,
  fallback = "",
  language = i18next.language,
) {
  if (!value) return fallback;
  if (typeof value === "string") return value;
  const preferred = language ? value[language.split("-")[0]] : undefined;
  if (typeof preferred === "string") return preferred;
  return value.en ?? value.es ?? fallsBackToFirstString(value, fallback);
}

/**
 * First string field of a multilingual object, or the fallback.
 * @param {object} value - A multilingual-shaped object.
 * @param {string} fallback - What to return when no field is a string.
 * @returns {string} The first string found, or the fallback.
 */
function fallsBackToFirstString(value, fallback) {
  const first = Object.values(value || {}).find(
    (candidate) => typeof candidate === "string",
  );
  return typeof first === "string" ? first : fallback;
}
