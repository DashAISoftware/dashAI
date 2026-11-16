/**
 * Column fields of an export schema.
 *
 * An exporter marks the schema fields whose value names dataset columns (a
 * target, columns to ignore...) with this key, set by ``column_field`` in the
 * backend. The export form reads the mark instead of knowing field names, so
 * any platform gets column selectors for its own fields.
 */
export const COLUMN_FIELD_KEY = "x-dashai-column";

/**
 * List the column fields declared by an exporter schema.
 *
 * @param {object|null} schema - The exporter's JSON schema.
 * @returns {Array<{key: string, title: string, description: string,
 *   multiple: boolean, required: boolean}>} One entry per column field, in
 *   schema order. ``required`` means a value must be picked: the field is
 *   required and does not accept null.
 */
export const getColumnFields = (schema) => {
  const properties = schema?.properties ?? {};
  const required = schema?.required ?? [];
  return Object.entries(properties)
    .filter(([, property]) => property?.[COLUMN_FIELD_KEY])
    .map(([key, property]) => {
      const nullable =
        Array.isArray(property.anyOf) &&
        property.anyOf.some((branch) => branch.type === "null");
      return {
        key,
        title: property.title ?? key,
        description: property.description ?? "",
        multiple: property[COLUMN_FIELD_KEY] === "multiple",
        required: required.includes(key) && !nullable,
      };
    });
};

/** Whether a column field has a value picked. */
export const isColumnFieldFilled = (field, value) =>
  field.multiple ? Array.isArray(value) && value.length > 0 : Boolean(value);

/** The value a column field sends: no columns is null for a list field. */
export const columnFieldParam = (field, value) => {
  if (field.multiple) return value?.length ? value : null;
  return value ?? "";
};
