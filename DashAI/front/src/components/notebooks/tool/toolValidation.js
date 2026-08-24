/**
 * Checks whether `converter` is usable given the columns currently
 * available (`datasetColumns`, shape: `{ id, columnName, valueType,
 * dataType, order }[]`). Extracted from `RightBar.jsx` so the session
 * wizard's converter sidebar can reuse the exact same compatibility
 * rules (allowed types/dtypes, input cardinality) against a different
 * column list (the session's input columns only, never the output
 * column) without drifting from the notebook flow's rules over time.
 */
export function validateConverter(converter, datasetColumns, t) {
  if (!datasetColumns.length) return { disabled: false, tooltip: "" };

  const allowedTypes = converter?.metadata?.allowed_types || [];
  const allowedDtypes = converter?.metadata?.allowed_dtypes || [];
  const inputCardinality = converter?.metadata?.input_cardinality || {};

  let validColumns = datasetColumns;
  let disabled = false;
  let tooltip =
    converter.description || converter.metadata?.short_description || "";

  if (allowedTypes.length > 0) {
    validColumns = validColumns.filter((col) =>
      allowedTypes.includes(col.valueType),
    );
  }

  if (allowedDtypes.length > 0) {
    validColumns = validColumns.filter((col) =>
      allowedDtypes.includes(col.dataType),
    );
  }

  if (inputCardinality.exact != null) {
    if (validColumns.length < inputCardinality.exact) {
      disabled = true;
      tooltip += `\n\n${t("datasets:error.requiresExactColumns", {
        required: inputCardinality.exact,
        available: validColumns.length,
        count: inputCardinality.exact,
      })}`;
    }
  } else if (inputCardinality.min != null) {
    if (validColumns.length < inputCardinality.min) {
      disabled = true;
      tooltip += `\n\n${t("datasets:error.requiresMinColumns", {
        required: inputCardinality.min,
        available: validColumns.length,
        count: inputCardinality.min,
      })}`;
    }
  }

  if (
    validColumns.length === 0 &&
    (allowedTypes.length > 0 || allowedDtypes.length > 0)
  ) {
    disabled = true;
    tooltip += `\n\n${t("datasets:error.noValidColumnsWithDtypesMentioned", {
      dtypes: [...allowedTypes, ...allowedDtypes].join(", "),
    })}`;
  }

  return { disabled, tooltip, validColumns };
}
