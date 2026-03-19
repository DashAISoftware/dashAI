import { useCallback } from "react";
import FormSchemaField from "./FormSchemaField";
import FormSchemaFieldWithOptions from "./FormSchemaFieldWithOptions";
import FormSchemaFieldWithCollapse from "./FormSchemaFieldWithCollapse";
import FormSchemaFieldWithOptimizers from "./FormSchemaFieldWithOptimizers";
import FormSchemaFieldWithParent from "./FormSchemaFieldWithParent";
import { getModelFromSubform } from "../../utils/schema";
import { Stack } from "@mui/material";

function SubField({
  objName,
  subField,
  fieldSubschema,
  subValue,
  subError,
  handleChange,
  setError,
}) {
  const field = {
    value: subValue,
    error: subError,
    onChange: handleChange(objName, subField),
  };

  return (
    <FormSchemaField
      key={`${objName}.${subField}`}
      objName={`${objName}.${subField}`}
      setError={setError}
      paramJsonSchema={fieldSubschema}
      field={field}
    />
  );
}

function FieldList({
  modelSchema,
  values,
  errors,
  handleChange,
  setError,
  errorsMessage,
}) {
  if (!modelSchema) return null;

  const fields = [];

  for (const key in modelSchema) {
    const fieldSchema = modelSchema[key];
    const objName = key;
    const value = values?.[objName];
    const error = errors?.[objName];
    const isOptimizable = fieldSchema.placeholder?.optimize !== undefined;

    const baseField = {
      value,
      error,
      onChange: handleChange(objName),
    };

    if ("anyOf" in fieldSchema) {
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
        fields.push(
          <FormSchemaFieldWithCollapse
            key={objName}
            name={objName}
            label={fieldSchema.title}
            description={fieldSchema.description}
            errorMessage={errorsMessage?.[objName]?.message}
          >
            {fieldSchema?.properties &&
              Object.keys(fieldSchema.properties).map((subField) => {
                const fieldSubschema = fieldSchema.properties[subField];
                const subValue = value?.[subField];
                const subError = error?.[subField];

                return (
                  <SubField
                    key={`${objName}.${subField}`}
                    objName={objName}
                    subField={subField}
                    fieldSubschema={fieldSubschema}
                    subValue={subValue}
                    subError={subError}
                    handleChange={handleChange}
                    setError={setError}
                  />
                );
              })}
          </FormSchemaFieldWithCollapse>,
        );
      }
    } else {
      fields.push(
        <FormSchemaField
          key={objName}
          objName={objName}
          paramJsonSchema={fieldSchema}
          field={baseField}
        />,
      );
    }
  }

  return fields;
}

function FormSchemaRenderFields({
  modelSchema,
  formik,
  autoSave,
  handleUpdateSchema,
  onFormSubmit,
  setError,
  errorsMessage,
  spacing = 2,
}) {
  // Handler to update formik values and trigger schema update
  const handleChange = useCallback(
    (name, subName) => (value) => {
      const fieldPath = subName ? `${name}.${subName}` : name;
      formik.setFieldValue(fieldPath, value, true);
      handleUpdateSchema(
        { [fieldPath]: value },
        autoSave ? onFormSubmit : null,
      );
    },
    [formik, handleUpdateSchema, autoSave, onFormSubmit],
  );

  if (!modelSchema) return null;

  return (
    <Stack spacing={spacing}>
      <FieldList
        modelSchema={modelSchema}
        values={formik?.values}
        errors={formik?.errors}
        handleChange={handleChange}
        setError={setError}
        errorsMessage={errorsMessage}
      />
    </Stack>
  );
}

export default FormSchemaRenderFields;
