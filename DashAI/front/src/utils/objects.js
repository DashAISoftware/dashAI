/**
 * Whether a value is a non-null, non-array object.
 * @param {*} value - Value to test.
 * @returns {boolean} True for a plain object.
 */
export function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
