import { formattedSubform } from "../../../../utils/schema";

function normalizeParentFieldValue(parent, value, fallbackPlaceholder) {
  if (value?.properties?.params?.comp) {
    return value;
  }

  const modelName = value?.component ?? fallbackPlaceholder?.component;
  const modelParams = value?.params ?? fallbackPlaceholder?.params ?? {};

  if (!modelName) {
    return value ?? null;
  }

  return formattedSubform({
    parent,
    model: modelName,
    params: modelParams,
  });
}

export function normalizeParamsForSchema(params = {}, schemaProperties = {}) {
  const normalized = { ...params };

  const defaultValueForAnyOf = (propertySchema) => {
    if (propertySchema.placeholder !== undefined) {
      return propertySchema.placeholder;
    }

    const anyOfOptions = propertySchema.anyOf || [];
    if (anyOfOptions.some((option) => option?.type === "null")) {
      return null;
    }

    const firstType = anyOfOptions[0]?.type;
    if (firstType === "integer" || firstType === "number") {
      return 0;
    }
    if (firstType === "boolean") {
      return false;
    }
    if (firstType === "array") {
      return [];
    }
    if (firstType === "object") {
      return {};
    }

    return "";
  };

  Object.keys(schemaProperties).forEach((key) => {
    const propertySchema = schemaProperties[key] || {};
    const currentValue = normalized[key];

    if (propertySchema.parent) {
      normalized[key] = normalizeParentFieldValue(
        propertySchema.parent,
        currentValue,
        propertySchema.placeholder,
      );
      return;
    }

    if (currentValue === undefined) {
      if (propertySchema.anyOf) {
        normalized[key] = defaultValueForAnyOf(propertySchema);
      } else {
        normalized[key] = propertySchema.placeholder ?? "";
      }
    }
  });

  return normalized;
}

export function buildDefaultValuesFromSchemaProperties(properties = {}) {
  return normalizeParamsForSchema({}, properties);
}

export function getInitialModelParameters({
  selectedModel,
  currentModelName,
  currentParams,
}) {
  if (!selectedModel) {
    return {};
  }

  let paramsSource;

  if (
    currentModelName === selectedModel.name &&
    currentParams &&
    Object.keys(currentParams).length > 0
  ) {
    paramsSource = currentParams;
  } else if (
    selectedModel.parameters &&
    Object.keys(selectedModel.parameters).length > 0
  ) {
    paramsSource = selectedModel.parameters;
  } else {
    paramsSource = buildDefaultValuesFromSchemaProperties(
      selectedModel.schema?.properties || {},
    );
  }

  return normalizeParamsForSchema(
    paramsSource,
    selectedModel.schema?.properties || {},
  );
}