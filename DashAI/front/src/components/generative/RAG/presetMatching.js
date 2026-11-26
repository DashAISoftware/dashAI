import { assertConfigurationValue, deepEqual } from "./configEquality";

/**
 * Parameter names a retriever preset match ignores, at every level of the
 * configuration (composite parents and each child, recursively).
 *
 * `top_k` is a slider: a composite splits it across its children, so it never
 * decides which preset a configuration belongs to. Mirrors the backend's
 * `_MATCH_IGNORED_KEYS` in `services/RAG/retriever_presets.py`.
 */
export const RETRIEVER_MATCH_IGNORED_KEYS = Object.freeze(["top_k"]);

/**
 * Whether a value is a non-null, non-array object.
 *
 * @param {unknown} value - The value to inspect.
 * @returns {boolean} True for a plain object-like value.
 */
function isObjectLike(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/**
 * Throw unless the ignored keys are an array.
 *
 * @param {unknown} ignoredKeys - The value to check.
 */
function assertIgnoredKeys(ignoredKeys) {
  if (!Array.isArray(ignoredKeys)) {
    throw new Error("ignoredKeys must be an array");
  }
}

/**
 * Whether a value is a usable `{component, params}` recipe reference.
 *
 * Usable means: a non-null, non-array object whose `component` is a non-empty
 * string and whose `params` is a non-null, non-array object. An absent `params`
 * is malformed, not an implicit `{}`. Whitespace is not trimmed, so a
 * whitespace-only component counts as a non-empty string.
 *
 * @param {unknown} value - The value to inspect.
 * @returns {boolean} True when the value is a usable reference.
 */
export function isPresetReference(value) {
  return (
    isObjectLike(value) &&
    typeof value.component === "string" &&
    value.component.length > 0 &&
    isObjectLike(value.params)
  );
}

/**
 * Throw unless the value is a usable `{component, params}` reference.
 *
 * @param {unknown} value - The value to check.
 * @param {string} name - How the value is named in the error message.
 * @throws {Error} When the value is not a usable reference.
 */
function assertPresetReference(value, name) {
  if (!isPresetReference(value)) {
    throw new Error(
      `${name} must be a {component, params} object with a non-empty string component and an object params`,
    );
  }
}

/**
 * Find the preset recipe a retriever or chunking reference matches.
 *
 * A match requires the same component and, after stripping `ignoredKeys` from
 * both sides, structurally equal params. Any other difference is a custom
 * configuration and yields null.
 *
 * Malformed input is an error, not a custom configuration: `ref` and every
 * entry of `presets` must satisfy `isPresetReference`, and every params value
 * must be within the configuration contract (see `configEquality.js`).
 *
 * @param {object} ref - The `{component, params}` reference to classify. Must
 *   satisfy `isPresetReference`.
 * @param {Array<object>} presets - Preset recipes, each `{component, params}`
 *   satisfying `isPresetReference`. Must be an array.
 * @param {ReadonlyArray<string>} ignoredKeys - Keys that never decide a match.
 *   Required and must be an array: pass NO_IGNORED_KEYS to compare every
 *   parameter.
 * @returns {object|null} The first matching preset, or null for a custom config.
 * @throws {Error} When `ignoredKeys` is not an array, when `presets` is not an
 *   array, when `ref` is not a usable reference, when any preset is not, or
 *   when a params value is outside the configuration contract.
 */
export function findMatchingPreset(ref, presets, ignoredKeys) {
  assertIgnoredKeys(ignoredKeys);
  assertPresetReference(ref, "ref");
  if (!Array.isArray(presets)) {
    throw new Error("presets must be an array");
  }
  presets.forEach((preset, index) =>
    assertPresetReference(preset, `presets[${index}]`),
  );

  assertConfigurationValue(ref.params, "ref.params");
  presets.forEach((preset, index) =>
    assertConfigurationValue(preset.params, `presets[${index}].params`),
  );

  return (
    presets.find(
      (preset) =>
        preset.component === ref.component &&
        deepEqual(preset.params, ref.params, ignoredKeys),
    ) ?? null
  );
}
