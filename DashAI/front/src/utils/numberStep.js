const DEFAULT_FLOAT_STEP = 0.1;

const numberBranch = (schema) =>
  schema?.type === "number"
    ? schema
    : (schema?.anyOf?.find((branch) => branch.type === "number") ?? schema);

const referenceValue = (placeholder) => {
  const value =
    placeholder !== null && typeof placeholder === "object"
      ? placeholder.fixed_value
      : placeholder;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
};

const isAligned = (value, step) => {
  const ratio = value / step;
  return Math.abs(ratio - Math.round(ratio)) < 1e-9;
};

/**
 * Resolve the increment the arrow controls of a float input should apply.
 *
 * An explicit ``step`` declared by the backend wins. Otherwise the step
 * follows the order of magnitude of the field's default value, capped at
 * 0.1, so a learning rate of 3e-5 moves by 1e-5 and a temperature of 0.7
 * moves by 0.1 instead of jumping a whole unit.
 *
 * @param {object} schema JSON schema of the field, carrying ``step`` and
 *   ``placeholder`` when the backend declares them
 * @returns {number} the step to set on the input
 */
export function resolveNumberStep(schema) {
  if (typeof schema?.step === "number" && schema.step > 0) {
    return schema.step;
  }
  const reference = referenceValue(schema?.placeholder);
  if (reference === null || reference === 0) {
    return DEFAULT_FLOAT_STEP;
  }
  const magnitude = Number(
    Math.pow(10, Math.floor(Math.log10(Math.abs(reference)))).toPrecision(1),
  );
  return Math.min(DEFAULT_FLOAT_STEP, magnitude);
}

/**
 * Build the native attributes of a float input from its JSON schema.
 *
 * Inclusive bounds become ``min`` and ``max`` so the arrows stop at the edge
 * of the valid range. ``min`` is only set when it lies on the step grid,
 * because the browser aligns stepped values to it and an offset minimum such
 * as 0.0001 would turn every value into 0.1001, 0.2001 and so on.
 *
 * @param {object} schema JSON schema of the field
 * @returns {object} ``step`` plus ``min`` and ``max`` when they apply
 */
export function numberInputAttributes(schema) {
  const step = resolveNumberStep(schema);
  const branch = numberBranch(schema);
  const attributes = { step };
  if (typeof branch?.minimum === "number" && isAligned(branch.minimum, step)) {
    attributes.min = branch.minimum;
  }
  if (typeof branch?.maximum === "number") {
    attributes.max = branch.maximum;
  }
  return attributes;
}
