import {
  getModelFromSubform,
  getParamsFromSubform,
} from "../../../utils/schema";

/** Parent class every prompt component inherits from. */
export const BASE_PROMPT_PARENT = "BasePrompt";

/** Language a prompt template falls back to when none is stored. */
export const DEFAULT_PROMPT_LANGUAGE = "en";

/** Param key holding the template text. */
export const PROMPT_TEMPLATE_PARAM = "template";

/** Param key holding the template language. */
export const PROMPT_LANGUAGE_PARAM = "language";

/** Param key holding a saved prompt's template map, keyed by language. */
export const PROMPT_TEMPLATES_PARAM = "templates";

/** Schema type a prompt field declares. */
const PROMPT_FIELD_TYPE = "object";

/** Suffix every prompt parent class ends with (`AgenticRerankerPrompt`, ...). */
const PROMPT_PARENT_SUFFIX = "Prompt";

/**
 * Whether a schema property describes a prompt component reference.
 *
 * Prompt properties are objects typed as a prompt parent (`BasePrompt` or a
 * descendant such as `AgenticRerankerPrompt`), which is what distinguishes
 * them from every other component reference in a schema.
 *
 * @param {object} fieldSchema - One property of a formatted model schema.
 * @returns {boolean} True when the property holds a prompt reference.
 */
export function isPromptFieldSchema(fieldSchema) {
  if (!fieldSchema || fieldSchema.type !== PROMPT_FIELD_TYPE) return false;
  const { parent } = fieldSchema;
  if (typeof parent !== "string") return false;
  return parent === BASE_PROMPT_PARENT || parent.endsWith(PROMPT_PARENT_SUFFIX);
}

/**
 * Read the component and params out of a prompt field value.
 *
 * Both accepted shapes are handled by the shared schema helpers: the canonical
 * `{component, params}` reference and the legacy nested subform shape produced
 * by `formattedSubform`.
 *
 * @param {object} value - The prompt field value.
 * @returns {{component: (string|null), params: object}} The selection.
 */
export function readPromptSelection(value) {
  const component = getModelFromSubform(value);
  const params = getParamsFromSubform(value);
  return {
    component: typeof component === "string" && component ? component : null,
    params: params && typeof params === "object" ? params : {},
  };
}

/**
 * Build the canonical prompt reference a prompt field stores.
 *
 * @param {string} component - The prompt component name.
 * @param {object} params - The params stored for that component.
 * @returns {{component: string, params: object}} The canonical reference.
 */
export function buildPromptRef(component, params) {
  return { component, params: { ...params } };
}

/**
 * Resolve the template to show for a prompt selection.
 *
 * An explicit non-blank stored template wins: it is what the user wrote and
 * what the pipeline will run. Otherwise the component's built-in template for
 * the requested language is used, then its English one, then any string it
 * ships.
 *
 * @param {object} [component] - The prompt component definition.
 * @param {object} [params] - The stored params of the selection.
 * @param {string} [language] - The language requested by the selection.
 * @returns {string} The template, or an empty string when there is none.
 */
export function resolvePromptTemplate(component, params, language) {
  const stored = params?.[PROMPT_TEMPLATE_PARAM];
  if (typeof stored === "string" && stored.trim()) return stored;

  const templates = component?.metadata?.templates;
  if (!templates) return "";

  for (const code of [language, DEFAULT_PROMPT_LANGUAGE]) {
    if (typeof templates[code] === "string") return templates[code];
  }

  const first = Object.values(templates).find(
    (candidate) => typeof candidate === "string" && candidate.trim(),
  );
  return first ?? "";
}

/**
 * List the languages a prompt component ships built-in templates for.
 *
 * @param {object} [component] - The prompt component definition.
 * @returns {string[]} The template language codes, empty when it ships none.
 */
export function promptTemplateLanguages(component) {
  const templates = component?.metadata?.templates;
  if (!templates || typeof templates !== "object") return [];
  return Object.keys(templates);
}

/**
 * Whether a stored template value is text a user would see.
 *
 * @param {*} value - One entry of a saved prompt's template map.
 * @returns {boolean} True for a string with visible content.
 */
function isTemplateText(value) {
  return typeof value === "string" && Boolean(value.trim());
}

/**
 * The template map a saved prompt stores in its parameters.
 *
 * Unlike `promptTemplateLanguages`, which lists what a component ships, these
 * helpers read what a library row saved: `parameters` holds either one
 * explicit `template` or a `templates` map keyed by language.
 *
 * @param {object} [parameters] - A library prompt's stored parameters.
 * @returns {object} Language code to template text, empty when it stores none.
 */
export function storedPromptTemplates(parameters) {
  const templates = parameters?.[PROMPT_TEMPLATES_PARAM];
  if (!templates || typeof templates !== "object" || Array.isArray(templates)) {
    return {};
  }
  return templates;
}

/**
 * List the languages a saved prompt stores a usable template for.
 *
 * A variant only counts when it holds text: an empty string is not something
 * the user can read or pick.
 *
 * @param {object} [parameters] - A library prompt's stored parameters.
 * @returns {string[]} The language codes with a non-blank template.
 */
export function storedPromptLanguages(parameters) {
  const templates = storedPromptTemplates(parameters);
  return Object.keys(templates).filter((code) =>
    isTemplateText(templates[code]),
  );
}

/**
 * Read how a saved prompt stores its templates and which variant it points at.
 *
 * A non-blank explicit `template` wins over the map, matching the resolution
 * below. Otherwise the row is a multi-language prompt: the stored `language`
 * when the map has that key, the first variant with text when it does not. The
 * stored key is kept even when its text is still empty, because that is the
 * variant an editor has to write and inherited rows point at it; the options a
 * user can pick come from `storedPromptLanguages` instead.
 *
 * @param {object} [parameters] - A library prompt's stored parameters.
 * @returns {{usesTemplates: boolean, language: (string|null)}} The stored shape
 *   and the language it is configured with.
 */
export function storedPromptShape(parameters) {
  const explicit = parameters?.[PROMPT_TEMPLATE_PARAM];
  const templates = storedPromptTemplates(parameters);
  const keys = Object.keys(templates);
  if (isTemplateText(explicit) || keys.length === 0) {
    return { usesTemplates: false, language: null };
  }
  const stored = parameters?.[PROMPT_LANGUAGE_PARAM];
  if (
    typeof stored === "string" &&
    Object.prototype.hasOwnProperty.call(templates, stored)
  ) {
    return { usesTemplates: true, language: stored };
  }
  return {
    usesTemplates: true,
    language: storedPromptLanguages(parameters)[0] ?? keys[0] ?? null,
  };
}

/**
 * Resolve the template a saved prompt stores in its parameters.
 *
 * A non-blank explicit `template` wins because it is what the pipeline runs.
 * Otherwise the requested language is used, then English, then the first
 * non-blank variant. `resolvePromptTemplate` above resolves a component's
 * built-in templates and is not interchangeable with this function.
 *
 * @param {object} [parameters] - A library prompt's stored parameters.
 * @param {string} [language] - The language to prefer.
 * @returns {string} The template, or an empty string when there is none.
 */
export function resolveStoredPromptTemplate(parameters, language) {
  const explicit = parameters?.[PROMPT_TEMPLATE_PARAM];
  if (isTemplateText(explicit)) return explicit;

  const templates = storedPromptTemplates(parameters);
  for (const code of [language, DEFAULT_PROMPT_LANGUAGE]) {
    if (code && isTemplateText(templates[code])) return templates[code];
  }

  const first = Object.values(templates).find(isTemplateText);
  return first ?? "";
}

/**
 * Whether a prompt component is a concrete default implementation.
 *
 * The base prompt schema only declares ``template``. Default prompt classes
 * extend it with a ``language`` parameter; the generic custom prompt classes
 * keep the base schema. The component schema is therefore the API-provided
 * distinction between a concrete default prompt and a container for a
 * user-written template.
 *
 * @param {object} [component] - The prompt component definition.
 * @returns {boolean} True for a concrete default prompt.
 */
export function isDefaultPromptComponent(component) {
  return Boolean(component?.schema?.properties?.language);
}

/**
 * Read a localized string out of an API text value.
 *
 * The API localizes `display_name`, so a plain string is already localized;
 * legacy multilingual objects fall back to their first non-blank string.
 *
 * @param {*} value - A plain or multilingual text value.
 * @returns {string} The text, or an empty string when it holds none.
 */
function readLocalizedText(value) {
  if (typeof value === "string") return value.trim() ? value : "";
  if (!value || typeof value !== "object") return "";
  return (
    Object.values(value).find(
      (candidate) => typeof candidate === "string" && candidate.trim(),
    ) ?? ""
  );
}

/**
 * Resolve a prompt component's label.
 *
 * Default prompt implementations have a localized `display_name` from the API.
 * Generic custom prompt classes inherit the base `display_name`; for those, the
 * component's own metadata name is the specific label (for example
 * "Custom Query Rewriting Prompt") and is used instead.
 *
 * @param {object} [component] - The prompt component definition.
 * @returns {string} The display name, or the component name when it has none.
 */
export function getPromptDisplayName(component) {
  const displayName = readLocalizedText(component?.display_name);
  const metadataName = readLocalizedText(component?.metadata?.name);
  if (isDefaultPromptComponent(component)) {
    return displayName || metadataName || component?.name || "";
  }
  return metadataName || displayName || component?.name || "";
}

/**
 * Read the placeholders a prompt template must contain.
 *
 * @param {object} [component] - The prompt component definition.
 * @returns {string[]} The required placeholders, empty when the component
 *   declares none.
 */
export function getPromptRequiredPlaceholders(component) {
  const required = component?.metadata?.required_placeholders;
  return Array.isArray(required) ? required : [];
}

/**
 * Read the description of each placeholder a prompt component declares.
 *
 * @param {object} [component] - The prompt component definition.
 * @returns {object} Map of placeholder to description, empty when none.
 */
export function getPromptPlaceholderDescriptions(component) {
  const descriptions = component?.metadata?.placeholder_descriptions;
  if (!descriptions || typeof descriptions !== "object") return {};
  return descriptions;
}

/**
 * List the required placeholders a template is missing.
 *
 * @param {object} [component] - The prompt component definition.
 * @param {string} template - The template to check.
 * @returns {string[]} The missing placeholders, empty when the template is
 *   complete.
 */
export function getMissingPromptPlaceholders(component, template) {
  const text = typeof template === "string" ? template : "";
  return getPromptRequiredPlaceholders(component).filter(
    (placeholder) => !text.includes(placeholder),
  );
}
