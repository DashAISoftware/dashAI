import React from 'react';
import useFormSchema from '../../../hooks/useFormSchema';
import FormSchemaButtonGroup from '../../../components/shared/FormSchemaButtonGroup';
import FormSchemaParameterContainer from '../../../components/shared/FormSchemaParameterContainer';
import FormSchemaRenderFields from './../../../components/shared/FormSchemaRenderFields';
import { FormSchemaProvider } from '../../../contexts/schema';
import PropTypes from 'prop-types';

function FormSchemaEmbeddedContainer({ children }) {
    return <FormSchemaProvider>{children}</FormSchemaProvider>;
}
FormSchemaEmbeddedContainer.propTypes = {
    children: PropTypes.node.isRequired,
};

function FormSchemaEmbeddedContent({ 
    model,
    initialValues,
    onFormSubmit,
    autoSave,
    onCancel,
    formSubmitRef,
    error,
    setError,
    errorsMessage,
    saveButtonText
    }) {
    const { formik, modelSchema, loading, handleUpdateSchema } = useFormSchema({
        model,
        initialValues,
        formSubmitRef,
        setError,
    });

    return (
        <>
            <FormSchemaParameterContainer>
                <FormSchemaRenderFields
                    modelSchema={modelSchema}
                    formik={formik}
                    autoSave={autoSave}
                    handleUpdateSchema={handleUpdateSchema}
                    onFormSubmit={onFormSubmit}
                    setError={setError}
                    errorsMessage={errorsMessage}
                />
            </FormSchemaParameterContainer>
            <FormSchemaButtonGroup
                onCancel={onCancel}
                onFormSubmit={onFormSubmit}
                autoSave={autoSave}
                formik={formik}
                error={error}
                saveButtonText={saveButtonText}
            />
        </>
    );
}


/**
 * This component renders a form schema for model configuration,
 * but instead of being in a dialog, it is embedded in the parent component.
 * @param {string} model string that describes a configurable object
 * @param {object} initialValues default values of the parameters, obtained from parameterSchema
 * @param {function} onFormSubmit  function that submits the form, receives the parameter values as a key-value object.
 * @param {bool} autoSave if true, the form will be submitted automatically when a parameter changes
 * @param {function} onCancel function to call when the cancel button is clicked
 * @param {object} formSubmitRef a reference to the formik object
 * @param {function} setError function to set an error in the form
 * @param {string} errorsMessage message to display when there are errors in the form
 * @returns {JSX.Element}
 */
function FormSchemaEmbedded({
    model,
    initialValues,
    onFormSubmit,
    autoSave,
    onCancel,
    formSubmitRef,
    setError,
    errorsMessage,
}) {
    return (
        <FormSchemaEmbeddedContainer>
            <FormSchemaEmbeddedContent
                model={model}
                initialValues={initialValues}
                onFormSubmit={onFormSubmit}
                autoSave={autoSave}
                onCancel={onCancel}
                formSubmitRef={formSubmitRef}
                setError={setError}
                errorsMessage={errorsMessage}
            />
        </FormSchemaEmbeddedContainer>
    );
}

FormSchemaEmbedded.propTypes = {
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
};

export default FormSchemaEmbedded;