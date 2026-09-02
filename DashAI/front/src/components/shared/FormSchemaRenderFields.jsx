import { useCallback, useMemo } from "react";
import FormSchemaField from "./FormSchemaField";
import FormSchemaFieldCard from "./FormSchemaFieldCard";
import FormSchemaFieldWithOptions from "./FormSchemaFieldWithOptions";
import FormSchemaFieldWithCollapse from "./FormSchemaFieldWithCollapse";
import FormSchemaFieldWithOptimizers from "./FormSchemaFieldWithOptimizers";
import FormSchemaFieldWithParent from "./FormSchemaFieldWithParent";
import { getModelFromSubform } from "../../utils/schema";
import { FormCardProvider } from "../../contexts/FormCardContext";
import { Box, Stack, Typography } from "@mui/material";
import PropTypes from "prop-types";

const getInitialValueFromSchema = (schema) => {
  if (schema.type !== "object") {
    return schema.placeholder;
  }

  return Object.keys(schema.properties ?? {}).reduce((acc, key) => {
    acc[key] = getInitialValueFromSchema(schema.properties[key]);
    return acc;
  }, {});
};

const resolveConditionalSchema = (schema, values) => {
  if (!schema?.dependsOn || !schema?.conditionalSchemas) {
    return schema;
  }

  const selectedValue = values?.[schema.dependsOn];
  const conditionalSchema = schema.conditionalSchemas[selectedValue];

  if (!conditionalSchema) {
    return schema;
  }

  return {
    ...schema,
    ...conditionalSchema,
    properties: conditionalSchema.properties ?? schema.properties,
  };
};

// Extracted to its own component so useMemo is called at the top level (Rules of Hooks)
function SubFieldItem({
  objName,
  subField,
  value,
  error,
  handleChange,
  setError,
  fieldSubschema,
}) {
  const subFieldObj = useMemo(
    () => ({
      value: value?.[subField],
      error: error?.[subField],
      onChange: handleChange(objName, subField),
    }),
    [value, error, objName, subField, handleChange],
  );

  return (
    <Box
      sx={{
        mb: 4,
        "& .MuiInputLabel-root": { display: "none" },
        "& .MuiOutlinedInput-notchedOutline legend > span": {
          display: "none",
        },
      }}
    >
      <SubFieldHeader
        label={fieldSubschema.title ?? subField}
        paramKey={subField}
      />
      <FormCardProvider>
        <FormSchemaField
          objName={`${objName}.${subField}`}
          setError={setError}
          paramJsonSchema={fieldSubschema}
          field={subFieldObj}
        />
      </FormCardProvider>
      {fieldSubschema.description && (
        <Typography
          variant="caption"
          color="text.disabled"
          sx={{ display: "block", mt: 2, lineHeight: 1.5 }}
        >
          {fieldSubschema.description}
        </Typography>
      )}
    </Box>
  );
}

function SubFieldHeader({ label, paramKey }) {
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="body2" fontWeight={600} color="text.primary">
        {label}
      </Typography>
      {paramKey && paramKey !== label && (
        <Typography
          component="span"
          variant="caption"
          color="text.secondary"
          sx={{ fontFamily: "monospace" }}
        >
          {paramKey}
        </Typography>
      )}
    </Box>
  );
}

SubFieldItem.propTypes = {
  objName: PropTypes.string.isRequired,
  subField: PropTypes.string.isRequired,
  value: PropTypes.any,
  error: PropTypes.any,
  handleChange: PropTypes.func.isRequired,
  setError: PropTypes.func,
  fieldSubschema: PropTypes.object.isRequired,
};

SubFieldHeader.propTypes = {
  label: PropTypes.string,
  paramKey: PropTypes.string,
};

function FormSchemaRenderFields({
  modelSchema,
  formik,
  autoSave,
  handleUpdateSchema,
  onFormSubmit,
  setError,
  errorsMessage,
  spacing = 1,
  excludeFields = [],
}) {
  if (!modelSchema) return null;

  const handleChange = useCallback(
    (name, subName) => (value) => {
      const fieldPath = subName ? `${name}.${subName}` : name;
      const dependentValues = {};

      formik.setFieldValue(fieldPath, value, true);
      // Always pass complete formik.values so handleUpdateSchema receives
      // ALL fields regardless of whether the context store has been
      // initialised yet (prevents race-condition with useEffect init).
      let updatedValues = { ...formik.values, [fieldPath]: value };

      if (subName) {
        // A sub-field also has to land nested, not only under its dotted path.
        updatedValues = {
          ...updatedValues,
          [name]: {
            ...(formik.values?.[name] ?? {}),
            [subName]: value,
          },
        };
      } else {
        Object.entries(modelSchema ?? {}).forEach(
          ([schemaKey, schemaValue]) => {
            if (
              schemaValue?.dependsOn === name &&
              schemaValue?.conditionalSchemas?.[value]
            ) {
              const dependentSchema = {
                ...schemaValue,
                ...schemaValue.conditionalSchemas[value],
                properties:
                  schemaValue.conditionalSchemas[value].properties ??
                  schemaValue.properties,
              };
              const initialValue = getInitialValueFromSchema(dependentSchema);
              dependentValues[schemaKey] = initialValue;
              formik.setFieldValue(schemaKey, initialValue, true);
            }
          },
        );
      }

      handleUpdateSchema(
        { ...updatedValues, ...dependentValues },
        autoSave ? onFormSubmit : null,
      );
    },
    [formik, handleUpdateSchema, modelSchema, autoSave, onFormSubmit],
  );

  const renderFields = useCallback(() => {
    const fields = [];

    for (const key in modelSchema) {
      // Fields the caller renders by hand: a schema field whose input needs
      // context the schema cannot carry, such as a dataset's column names.
      if (excludeFields.includes(key)) continue;

      const fieldSchema = resolveConditionalSchema(
        modelSchema[key],
        formik?.values,
      );
      const objName = key;
      const value = formik?.values?.[objName];
      const error = formik?.errors?.[objName];
      const isOptimizable = fieldSchema.placeholder?.optimize !== undefined;

      const baseField = {
        value,
        error,
        onChange: handleChange(objName),
      };

      if ("anyOf" in fieldSchema) {
        // FormSchemaFieldWithOptions renders its own card
        fields.push(
          <FormSchemaFieldWithOptions
            key={objName}
            title={fieldSchema.title}
            description={fieldSchema.description}
            options={fieldSchema.anyOf}
            required={fieldSchema.required}
            objName={objName}
            setError={setError}
            field={baseField}
          />,
        );
      } else if (isOptimizable) {
        // FormSchemaFieldWithOptimizers renders its own card
        fields.push(
          <FormSchemaFieldWithOptimizers
            key={objName}
            objName={objName}
            paramJsonSchema={fieldSchema}
            field={baseField}
          />,
        );
      } else if (fieldSchema.type === "object") {
        if (Boolean(fieldSchema?.parent)) {
          // FormSchemaFieldWithParent renders its own card
          fields.push(
            <FormSchemaFieldWithParent
              key={objName}
              name={objName}
              field={baseField}
              selectedModel={getModelFromSubform(value)}
              label={fieldSchema.title}
              description={fieldSchema.description}
            />,
          );
        } else {
          // FormSchemaFieldWithCollapse renders its own card
          fields.push(
            <FormSchemaFieldWithCollapse
              key={objName}
              name={objName}
              label={fieldSchema.title}
              description={fieldSchema.description}
              errorMessage={errorsMessage?.[objName]?.message}
              defaultExpanded={Boolean(fieldSchema?.dependsOn)}
            >
              {fieldSchema?.properties &&
                Object.keys(fieldSchema.properties).map((subField) => (
                  <SubFieldItem
                    key={`${objName}.${subField}`}
                    objName={objName}
                    subField={subField}
                    value={value}
                    error={error}
                    handleChange={handleChange}
                    setError={setError}
                    fieldSubschema={fieldSchema.properties[subField]}
                  />
                ))}
            </FormSchemaFieldWithCollapse>,
          );
        }
      } else {
        // Simple scalar fields — wrap in a card here
        fields.push(
          <FormSchemaFieldCard
            key={objName}
            label={fieldSchema.title}
            paramKey={objName}
            description={fieldSchema.description}
          >
            <FormSchemaField
              objName={objName}
              paramJsonSchema={fieldSchema}
              field={baseField}
            />
          </FormSchemaFieldCard>,
        );
      }
    }

    return fields;
  }, [
    modelSchema,
    formik.values,
    formik.errors,
    handleChange,
    setError,
    errorsMessage,
    excludeFields,
  ]);

  return <Stack spacing={spacing}>{renderFields()}</Stack>;
}

FormSchemaRenderFields.propTypes = {
  modelSchema: PropTypes.object,
  formik: PropTypes.object.isRequired,
  autoSave: PropTypes.bool,
  handleUpdateSchema: PropTypes.func.isRequired,
  onFormSubmit: PropTypes.func,
  setError: PropTypes.func,
  errorsMessage: PropTypes.object,
  spacing: PropTypes.number,
  excludeFields: PropTypes.arrayOf(PropTypes.string),
};

export default FormSchemaRenderFields;
