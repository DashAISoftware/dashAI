import PropTypes from "prop-types";
import useFormSchema from "../../../../hooks/useFormSchema";
import FormSchemaButtonGroup from "../../../../components/shared/FormSchemaButtonGroup";
import FormSchemaParameterContainer from "../../../../components/shared/FormSchemaParameterContainer";
import RAGFormSchemaRenderFields from "./RAGFormSchemaRenderFields";

/**
 * RAG-specific version of FormSchema that uses RAGFormSchemaRenderFields
 * for proper handling of nested model parameters (with working modal).
 * 
 * All other functionality remains the same as the generic FormSchema.
 */
function RAGFormSchema({
  model,
  initialValues,
  onFormSubmit,
  autoSave,
  onCancel,
  formSubmitRef,
  error,
  setError,
  errorsMessage,
  saveButtonText,
  onValuesChange,
  showBorder = true,
  hideButtons = false,
}) {
  const { formik, modelSchema, loading, handleUpdateSchema } = useFormSchema({
    model,
    initialValues,
    formSubmitRef,
    setError,
    onValuesChange,
  });

  return (
    <>
      <FormSchemaParameterContainer showBorder={showBorder}>
        <RAGFormSchemaRenderFields
          modelSchema={modelSchema}
          formik={formik}
          autoSave={autoSave}
          handleUpdateSchema={handleUpdateSchema}
          onFormSubmit={onFormSubmit}
          setError={setError}
          errorsMessage={errorsMessage}
        />
      </FormSchemaParameterContainer>

      {!hideButtons && (
        <FormSchemaButtonGroup
          onCancel={onCancel}
          onFormSubmit={onFormSubmit}
          autoSave={autoSave}
          formik={formik}
          error={error}
          saveButtonText={saveButtonText}
        />
      )}
    </>
  );
}

RAGFormSchema.propTypes = {
  model: PropTypes.string,
  initialValues: PropTypes.object,
  onFormSubmit: PropTypes.func,
  autoSave: PropTypes.bool,
  onCancel: PropTypes.func,
  extraOptions: PropTypes.shape({}),
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }),
  setError: PropTypes.func,
  errorsMessage: PropTypes.object,
  saveButtonText: PropTypes.string,
  onValuesChange: PropTypes.func,
  showBorder: PropTypes.bool,
  hideButtons: PropTypes.bool,
};

export default RAGFormSchema;
