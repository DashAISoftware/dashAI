import * as Yup from "yup";

type SchemaProperty = {
  type: string | string[];
  title?: string;
  nullable?: boolean;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  default?: any;
  placeholder?: any;
  [key: string]: any;
};

type SchemaProperties = {
  [key: string]: SchemaProperty;
};

/**
 * Preprocesses the schema properties to handle nullable types.
 * If a property has an `anyOf` with two items, where the second is `null`,
 * it replaces the property with the first item and marks it as nullable.
 *
 * @param properties - The schema properties to preprocess.
 * @returns The preprocessed schema properties.
 */
export function preprocessSchema(
  properties: SchemaProperties,
): SchemaProperties {
  const newProps = { ...properties };

  for (const key in newProps) {
    if (!("anyOf" in newProps[key])) continue;

    if (newProps[key].anyOf.length !== 2) continue;

    if (newProps[key].anyOf[1].type === "null") {
      let replaceProp = newProps[key].anyOf[0];
      replaceProp.title = newProps[key].title;
      replaceProp.nullable = true;
      newProps[key] = replaceProp;
    }
  }
  return newProps;
}

/**
 * Builds a Yup validation schema from the given properties.
 * It supports various types like integer, number, string, and boolean,
 * and applies constraints based on the property definitions.
 *
 * @param properties - The schema properties to build the Yup schema from.
 * @returns A Yup object schema.
 */
export function buildYupSchema(
  properties: SchemaProperties,
): Yup.ObjectSchema<any> {
  const shape: Record<string, any> = {};
  for (const key in properties) {
    const prop = properties[key];
    let validator;
    switch (prop.type) {
      case "integer":
      case "number":
        validator = Yup.number();
        if (prop.minimum !== undefined) validator = validator.min(prop.minimum);
        if (prop.maximum !== undefined) validator = validator.max(prop.maximum);
        if (prop.type === "integer") validator = validator.integer();
        break;
      case "string":
        validator = Yup.string();
        if (prop.minLength !== undefined)
          validator = validator.min(prop.minLength);
        if (prop.maxLength !== undefined)
          validator = validator.max(prop.maxLength);
        break;
      case "boolean":
        validator = Yup.boolean();
        break;
      default:
        validator = Yup.mixed();
    }
    if (prop.default === undefined && prop.nullable !== true) {
      validator = validator.required("Required");
    }
    shape[key] = validator;
  }
  return Yup.object().shape(shape);
}
