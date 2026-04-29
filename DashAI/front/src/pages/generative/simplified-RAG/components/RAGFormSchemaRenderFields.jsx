import { useCallback } from "react";
import RAGFormSchemaFieldWithParent from "./RAGFormSchemaFieldWithParent";
import FormSchemaFieldWithOptions from "../../../../components/shared/FormSchemaFieldWithOptions";
import FormSchemaFieldWithCollapse from "../../../../components/shared/FormSchemaFieldWithCollapse";
import FormSchemaFieldWithOptimizers from "../../../../components/shared/FormSchemaFieldWithOptimizers";
import FormSchemaField from "../../../../components/shared/FormSchemaField";
import { getModelFromSubform } from "../../../../utils/schema";
import { Stack } from "@mui/material";
import PropTypes from "prop-types";


/**
 * RAG-specific version of FormSchemaRenderFields that uses RAGFormSchemaFieldWithParent
 * for handling nested model parameters instead of the generic version.
 */
function SubFieldItem({
  objName,
  subField,
  value,
  error,
  handleChange,
  setError,
  fieldSubschema,
}) {
  return (
    <FormSchemaField
      objName={`${objName}.${subField}`}
      setError={setError}
      paramJsonSchema={fieldSubschema}
      field={{
        value: value?.[subField],
        error: error?.[subField],
        onChange: handleChange(objName, subField),
      }}
    />
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

function RAGFormSchemaRenderFields({
  modelSchema,
  formik,
  autoSave,
  handleUpdateSchema,
  onFormSubmit,
  setError,
  errorsMessage,
  spacing = 1,
}) {
  if (!modelSchema) return null;

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

  const renderFields = useCallback(() => {
    const fields = [];

    for (const key in modelSchema) {
      const fieldSchema = modelSchema[key];
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
          // RAG: Use RAGFormSchemaFieldWithParent instead of generic version
          fields.push(
            <RAGFormSchemaFieldWithParent
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
            </FormSchemaFieldWithCollapse>
          );
        }
      }
    }
    return fields;
  }, [modelSchema, formik, handleChange, setError, errorsMessage]);

  return (
    <Stack spacing={spacing} data-testid="render-fields">
      {renderFields()}
    </Stack>
  );
}

RAGFormSchemaRenderFields.propTypes = {
  modelSchema: PropTypes.object,
  formik: PropTypes.object.isRequired,
  autoSave: PropTypes.bool,
  handleUpdateSchema: PropTypes.func.isRequired,
  onFormSubmit: PropTypes.func,
  setError: PropTypes.func,
  errorsMessage: PropTypes.object,
  spacing: PropTypes.number,
};

export default RAGFormSchemaRenderFields;
