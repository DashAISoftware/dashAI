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

/** Schema type a prompt field declares. */
const PROMPT_FIELD_TYPE = "object";

/** Suffix every prompt parent class ends with (`LLMFilterPrompt`, ...). */
const PROMPT_PARENT_SUFFIX = "Prompt";

/** `metadata.variant` value of a hand-written prompt component. */
const CUSTOM_PROMPT_VARIANT = "custom";

/** Name prefix of hand-written prompt components. */
const CUSTOM_PROMPT_PREFIX = "Custom";

/**
 * Whether a schema property describes a prompt component reference.
 *
 * Prompt properties are objects typed as a prompt parent (`BasePrompt` or a
 * descendant such as `LLMFilterPrompt`), which is what distinguishes them from
 * every other component reference in a schema.
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
 * Whether a prompt component holds a hand-written template.
 *
 * Custom prompts are the ones a user's text can be stored under, so they are
 * the target of the "new prompt" action.
 *
 * @param {object} [component] - The prompt component definition.
 * @returns {boolean} True for a custom prompt component.
 */
export function isCustomPromptComponent(component) {
  if (!component) return false;
  if (component.metadata?.variant === CUSTOM_PROMPT_VARIANT) return true;
  return (
    typeof component.name === "string" &&
    component.name.startsWith(CUSTOM_PROMPT_PREFIX)
  );
}

/**
 * Resolve a prompt component's label.
 *
 * The API localizes `display_name` for the request's `Accept-Language`, so a
 * plain string is already localized; legacy multilingual objects fall back to
 * their first string.
 *
 * @param {object} [component] - The prompt component definition.
 * @returns {string} The display name, or the component name when it has none.
 */
export function getPromptDisplayName(component) {
  const displayName = component?.display_name;
  if (typeof displayName === "string" && displayName.trim()) return displayName;
  if (displayName && typeof displayName === "object") {
    const localized = Object.values(displayName).find(
      (candidate) => typeof candidate === "string" && candidate.trim(),
    );
    if (localized) return localized;
  }
  return component?.name ?? "";
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
