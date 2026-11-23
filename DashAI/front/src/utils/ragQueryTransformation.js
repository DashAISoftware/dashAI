/**
 * Pure helpers shared by the query transformation picker and its advanced
 * modal.
 *
 * They live here rather than in either component so the picker and the modal
 * can both use them without importing each other: the picker renders the modal,
 * so a modal-to-picker import closes a cycle.
 */

import i18next from "i18next";
import {
  DEFAULT_PROMPT_LANGUAGE,
  LLM_MODEL_KEY,
  PROMPT_KEY,
  PROMPT_VARIANT_DEFAULT,
} from "../constants/rag";
import { resolveLocalizedText } from "./localize";

/** The params of a ref that stores none. */
const NO_PARAMS = Object.freeze({});

/**
 * The i18n key suffixes (under `rag.config.queryTransformation`) that explain
 * why the stage cannot be enabled or saved.
 */
export const QUERY_TRANSFORMATION_BLOCK = Object.freeze({
  INCOMPLETE: "incomplete",
  NEEDS_DOWNLOADED_MODEL: "needsDownloadedModel",
  PROMPT_REQUIRED: "promptRequired",
  COMPOSITE_INCOMPLETE: "compositeIncomplete",
});

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
  const declaring = transformers.find(
    (component) =>
      component.schema?.properties?.[LLM_MODEL_KEY]?.placeholder?.component,
  );
  return (
    declaring?.schema.properties[LLM_MODEL_KEY].placeholder.component ?? null
  );
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
  const downloaded = generators.filter((generator) => generator.downloaded);
  return (
    downloaded.find((generator) => generator.name === defaultName) ??
    downloaded[0] ??
    null
  );
}

/**
 * The params of a stage ref. A ref without `params` is the minimal ref
 * `{component}`, whose params are empty.
 * @param {{component: string, params: (object|undefined)}} ref - The stage ref.
 * @returns {object} The ref's params.
 */
export function stageParams(ref) {
  return ref.params ?? NO_PARAMS;
}

/**
 * Whether a stage ref carries the two references the backend requires on save:
 * the transformation LLM (`llm_model`) and the prompt.
 * @param {object|null} ref - The `{component, params}` stage ref.
 * @returns {boolean} True when both references name a component.
 */
export function isCompleteQueryTransformationRef(ref) {
  return Boolean(
    ref?.params?.[LLM_MODEL_KEY]?.component &&
    ref?.params?.[PROMPT_KEY]?.component,
  );
}

/**
 * Whether a generation model is known and downloaded.
 * @param {Array} generators - The generator components from the API.
 * @param {string|undefined} name - The generator name to look up.
 * @returns {boolean} True when the model exists and is downloaded.
 */
export function isGeneratorDownloaded(generators, name) {
  const generator = generators.find((item) => item.name === name);
  return generator?.downloaded === true;
}

/**
 * Whether a stage ref may be persisted: it carries its LLM and prompt, and the
 * LLM is downloaded, so the backend would not reject it at run time.
 * @param {object|null} ref - The `{component, params}` stage ref.
 * @param {Array} generators - The generator components from the API.
 * @returns {boolean} True when the ref can be saved.
 */
export function canPersistQueryTransformationRef(ref, generators) {
  return (
    isCompleteQueryTransformationRef(ref) &&
    isGeneratorDownloaded(generators, ref.params[LLM_MODEL_KEY].component)
  );
}

/**
 * Build the `{component, params}` reference a freshly enabled stage PUTs.
 *
 * The backend fills omitted defaults server-side, but it validates that
 * `llm_model` and `prompt` are present, so both are seeded here: the generator
 * the caller resolved (a downloaded model, see `resolveEnableGenerator`)
 * and the technique's default prompt. Everything else, the optional reranker
 * included, is left out so the server supplies its default.
 *
 * @param {object} transformerComponent - The transformer component to enable.
 * @param {string} technique - Its `metadata.technique`, to pick the prompt.
 * @param {object|null} generator - The generator to seed, if any.
 * @param {Array} prompts - The transformation prompts to choose from.
 * @returns {object} The `{component, params}` session parameter value.
 */
export function buildQueryTransformationRef(
  transformerComponent,
  technique,
  generator,
  prompts,
) {
  const params = {};
  if (generator) {
    params[LLM_MODEL_KEY] = { component: generator.name, params: {} };
  }
  const defaultPrompt = prompts.find(
    (prompt) =>
      prompt.metadata?.technique === technique &&
      prompt.metadata?.variant === PROMPT_VARIANT_DEFAULT,
  );
  if (defaultPrompt) {
    params[PROMPT_KEY] = {
      component: defaultPrompt.name,
      params: { language: DEFAULT_PROMPT_LANGUAGE },
    };
  }
  return { component: transformerComponent.name, params };
}

/**
 * Decide what enabling the stage with a transformer persists, or why it cannot.
 *
 * @param {object} options
 * @param {object} options.transformer - The transformer component to enable.
 * @param {Array} options.generators - The generator components from the API.
 * @param {string|null} options.defaultGeneratorName - The backend default.
 * @param {Array} options.prompts - The transformation prompts.
 * @returns {{ref: (object|null), blockedBy: (string|null)}} The ref to persist,
 *   or the i18n key suffix of the reason it cannot be enabled.
 */
export function prepareEnableRef({
  transformer,
  generators,
  defaultGeneratorName,
  prompts,
}) {
  const generator = resolveEnableGenerator(generators, defaultGeneratorName);
  if (!generator) {
    return {
      ref: null,
      blockedBy: QUERY_TRANSFORMATION_BLOCK.NEEDS_DOWNLOADED_MODEL,
    };
  }
  const ref = buildQueryTransformationRef(
    transformer,
    transformer?.metadata?.technique,
    generator,
    prompts,
  );
  if (!isCompleteQueryTransformationRef(ref)) {
    return { ref: null, blockedBy: QUERY_TRANSFORMATION_BLOCK.PROMPT_REQUIRED };
  }
  return { ref, blockedBy: null };
}

/**
 * Resolves a component's display name or description, whether the API shipped
 * it as a localized string or as a multilingual object.
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
  return resolveLocalizedText(value, language) || fallback;
}
