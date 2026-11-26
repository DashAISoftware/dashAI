/**
 * Structural equality for RAG configurations.
 *
 * Mirrors the backend contract in `DashAI/back/services/RAG/config_equality.py`
 * (`configs_equal`). Both implementations read the same examples from
 * `tests/shared/config_equality_cases.json`.
 *
 * Contract
 * --------
 * Values: `null`, booleans, finite numbers, strings, arrays, and plain objects
 * with string keys. Anything else (functions, symbols, bigints, Date, Map, Set,
 * class instances, NaN, Infinity, and `undefined` outside an object property)
 * throws an Error. Nothing is silently defaulted. Integral numbers (including
 * floats such as 1e20) beyond +/-(2^53-1) are rejected because JavaScript cannot
 * represent them exactly; fractional floats are unaffected.
 *
 * Objects are equal iff, after dropping the ignored keys, they have exactly the
 * same keys and equal values. Key order is irrelevant. There are no subsets: an
 * extra or a missing key makes two objects different.
 *
 * Arrays are equal iff they have the same length and are element-wise equal in
 * order.
 *
 * Strict types: a boolean never equals a number (`false` is not `0`, `true` is
 * not `1`). `null` never equals an absent key. Numbers compare by value, and `1`
 * equals `1.0`; JavaScript cannot tell the two apart, so the contract does not
 * either. Strings never equal numbers.
 *
 * Ignored keys: an explicit array of key names, applied recursively at every
 * object level, including objects inside arrays and inside component references'
 * `params`. It defaults to none.
 *
 * `undefined` in JavaScript: an object property whose value is `undefined` is
 * treated as absent, because that is what JSON and the wire carry. `undefined`
 * anywhere else (the top-level argument, an array element) is malformed and
 * throws.
 *
 * Both inputs are validated completely before anything is compared. A malformed
 * value throws even when the comparison would stop earlier, and the result never
 * depends on evaluation order.
 */

/**
 * Ignored-key list that ignores nothing: every parameter is compared.
 */
export const NO_IGNORED_KEYS = Object.freeze([]);

const ROOT_PATH = "$";

/**
 * Whether a value is a plain object: its prototype is `Object.prototype` or
 * `null`. Dates, Maps, Sets and class instances are not plain objects.
 *
 * @param {unknown} value - The value to inspect.
 * @returns {boolean} True for a plain object.
 */
function isPlainObject(value) {
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

/**
 * Classify a value into one of the contract categories. Mirrors the
 * backend, which rejects integral numbers beyond +/-(2^53-1). Every float at or
 * above 2^53 is integral, so the check covers all of them.
 *
 * @param {unknown} value - The value to classify.
 * @param {string} path - Location of the value, used in error messages.
 * @returns {"null"|"boolean"|"number"|"string"|"array"|"object"} The category.
 *
 * @throws {Error} When the value is outside the contract, including
 *   `undefined`, a non-finite number, or an integral number (including floats
 *   such as 1e20) beyond +/-(2^53-1).
 */
function kindOf(value, path) {
  if (value === null) return "null";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error(
        `${path}: non-finite number ${value} has no configuration equality`,
      );
    }
    if (Number.isInteger(value) && !Number.isSafeInteger(value)) {
      throw new Error(
        `${path}: integer ${value} is outside +/-(2^53-1) and cannot be compared exactly`,
      );
    }
    return "number";
  }
  if (typeof value === "string") return "string";
  if (Array.isArray(value)) return "array";
  if (typeof value === "object" && isPlainObject(value)) return "object";
  const typeName = value === undefined ? "undefined" : typeof value;
  throw new Error(
    `${path}: unsupported configuration value of type ${typeName}`,
  );
}

/**
 * Check that a value and everything nested in it is within the contract.
 *
 * Object properties whose value is `undefined` are absent and are skipped.
 * Arrays are walked by index, not with forEach: forEach skips holes, and a hole
 * reads as `undefined`, which is malformed here.
 *
 * @param {unknown} value - The value to check.
 * @param {string} path - Location of the value, used in error messages.
 * @throws {Error} When the value or a nested value is outside the contract.
 */
function validate(value, path) {
  const kind = kindOf(value, path);
  if (kind === "array") {
    for (let index = 0; index < value.length; index += 1) {
      validate(value[index], `${path}[${index}]`);
    }
    return;
  }
  if (kind === "object") {
    if (Object.getOwnPropertySymbols(value).length > 0) {
      throw new Error(`${path}: object keys must be strings, not symbols`);
    }
    for (const key of Object.keys(value)) {
      if (value[key] === undefined) continue;
      validate(value[key], `${path}.${key}`);
    }
  }
}

/**
 * Check that a value is within the configuration contract.
 *
 * Use this to reject malformed input before a comparison that might stop
 * early. `deepEqual` runs the same check on both of its arguments.
 *
 * @param {unknown} value - The value to check.
 * @param {string} [name="value"] - How the value is named in the error message.
 * @throws {Error} When the value or a nested value is outside the contract.
 */
export function assertConfigurationValue(value, name = "value") {
  validate(value, name);
}

/**
 * Check that ignored keys are an array of key names.
 *
 * @param {unknown} ignoredKeys - The value to check.
 * @returns {Set<string>} The key names.
 * @throws {Error} When `ignoredKeys` is not an array or holds a non-string.
 */
function ignoredNames(ignoredKeys) {
  if (!Array.isArray(ignoredKeys)) {
    throw new Error("ignoredKeys must be an array of key names");
  }
  for (const name of ignoredKeys) {
    if (typeof name !== "string") {
      throw new Error(`ignored key names must be strings, got ${typeof name}`);
    }
  }
  return new Set(ignoredKeys);
}

/**
 * The kept entries of a validated object: defined values whose keys are not
 * ignored. A Map is used so keys such as `__proto__` are plain data.
 *
 * @param {object} object - A validated object.
 * @param {Set<string>} ignored - Key names to drop at this level.
 * @returns {Map<string, unknown>} The kept entries.
 */
function keptEntries(object, ignored) {
  const kept = new Map();
  for (const key of Object.keys(object)) {
    if (ignored.has(key) || object[key] === undefined) continue;
    kept.set(key, object[key]);
  }
  return kept;
}

/**
 * Compare two validated arrays element by element, in order. Walks by index,
 * matching `validate`, since validated arrays have no holes.
 *
 * @param {Array} left - First array.
 * @param {Array} right - Second array.
 * @param {Set<string>} ignored - Key names ignored inside the elements.
 * @returns {boolean} True when the lengths match and every pair is equal.
 */
function sameArray(left, right, ignored) {
  if (left.length !== right.length) return false;
  for (let index = 0; index < left.length; index += 1) {
    if (!sameValue(left[index], right[index], ignored)) return false;
  }
  return true;
}

/**
 * Compare two validated objects: same kept keys with equal values.
 *
 * @param {object} left - First object.
 * @param {object} right - Second object.
 * @param {Set<string>} ignored - Key names dropped at every level.
 * @returns {boolean} True when the kept keys are identical and values equal.
 */
function sameObject(left, right, ignored) {
  const leftKept = keptEntries(left, ignored);
  const rightKept = keptEntries(right, ignored);
  if (leftKept.size !== rightKept.size) return false;
  for (const [key, item] of leftKept) {
    if (!rightKept.has(key)) return false;
    if (!sameValue(item, rightKept.get(key), ignored)) return false;
  }
  return true;
}

/**
 * Compare two validated values. Values of different categories are never
 * equal. Both values must already be validated, so `kindOf` never reports a
 * path here.
 *
 * @param {unknown} left - First value, already validated.
 * @param {unknown} right - Second value, already validated.
 * @param {Set<string>} ignored - Key names dropped at every object level.
 * @returns {boolean} True when the values are equal under the contract.
 */
function sameValue(left, right, ignored) {
  const kind = kindOf(left, ROOT_PATH);
  if (kind !== kindOf(right, ROOT_PATH)) return false;
  if (kind === "null") return true;
  if (kind === "array") return sameArray(left, right, ignored);
  if (kind === "object") return sameObject(left, right, ignored);
  return left === right;
}

/**
 * Return whether two RAG configuration values are equal under the contract.
 *
 * Both arguments are validated completely before anything is compared, so a
 * malformed value throws even when the first difference would be found early.
 *
 * @param {unknown} left - First configuration value. Must be within the
 *   contract; `undefined` is malformed here.
 * @param {unknown} right - Second configuration value, same rules.
 * @param {ReadonlyArray<string>} [ignoredKeys=NO_IGNORED_KEYS] - Key names
 *   dropped at every object level, including objects inside arrays and nested
 *   component references' params. Must be an array of strings.
 * @returns {boolean} True when the two values are equal.
 * @throws {Error} When either value is outside the contract (functions,
 *   symbols, bigints, Date, Map, Set, class instances, NaN, Infinity, an
 *   integral number (including floats such as 1e20) beyond +/-(2^53-1), or
 *   `undefined` outside an object property,
 *   including an array hole), when `ignoredKeys` is not an
 *   array of strings, or when an object key is a symbol.
 */
export function deepEqual(left, right, ignoredKeys = NO_IGNORED_KEYS) {
  const ignored = ignoredNames(ignoredKeys);
  validate(left, "left");
  validate(right, "right");
  return sameValue(left, right, ignored);
}
