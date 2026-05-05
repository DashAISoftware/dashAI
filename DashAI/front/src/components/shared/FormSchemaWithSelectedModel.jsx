import { Stack } from "@mui/material";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useFormSchemaStore } from "../../contexts/schema";
import FormSchemaBreadScrumbs from "./FormSchemaBreadScrumbs";
import FormSchema from "./FormSchema";
import FormSchemaModelSelect from "./FormSchemaModelSelect";
import PropTypes from "prop-types";

/**
 * This component is a form schema with a selected model
 * @param {string} modelToConfigure - The model to configure
 * @param {object} initialValues - The initial values of the form
 * @param {function} onFormSubmit - The function to submit the form
 * @param {function} onCancel - The function to cancel the form
 */

function FormSchemaWithSelectedModel({
  modelToConfigure,
  initialValues,
  onFormSubmit,
  onCancel,
  saveButtonText,
  hideButtons,
  onValuesChange = () => {},
  formSubmitRef,
  onErrorChange,
}) {
  const {
    formValues,
    properties,
    propertyData,
    valuesByProperties,
    removeLastProperty,
    setErrorForm,
    errorForm,
  } = useFormSchemaStore();

  const [selectedModel, setSelectedModel] = useState(
    modelToConfigure || propertyData?.model,
  );

  const selectedProperty = Boolean(propertyData?.selected);

  const defaultValues = useMemo(() => {
    if (selectedProperty) {
      if (propertyData.params) {
        return propertyData.params;
      } else return null;
    }

    return initialValues ?? valuesByProperties;
  }, [
    selectedProperty,
    propertyData.params,
    initialValues,
    valuesByProperties,
  ]);

  useEffect(() => {
    if (propertyData.model) {
      setSelectedModel(propertyData.model);
    } else {
      setSelectedModel(modelToConfigure);
    }
  }, [propertyData.model, propertyData.params, modelToConfigure]);

  useEffect(() => {
    if (formSubmitRef) {
      formSubmitRef.current = () => onFormSubmit(formValues);
    }
  }, [formValues, onFormSubmit, formSubmitRef]);

  useEffect(() => {
    if (onErrorChange) {
      onErrorChange(errorForm);
    }
  }, [errorForm, onErrorChange]);

  return (
    <Stack spacing={2} sx={{ py: 2 }}>
      {Boolean(propertyData?.parent) && (
        <>
          <FormSchemaBreadScrumbs />
          <FormSchemaModelSelect
            parent={propertyData.parent}
            selectedModel={selectedModel}
            onChange={setSelectedModel}
          />
        </>
      )}

      <FormSchema
        model={selectedModel}
        initialValues={defaultValues}
        onFormSubmit={() => onFormSubmit(formValues)}
        setError={setErrorForm}
        saveButtonText={saveButtonText}
        hideButtons={hideButtons}
        onValuesChange={() => onValuesChange(formValues)}
        onCancel={() => {
          if (properties.length > 0) {
            removeLastProperty();
          } else {
            onCancel();
          }
        }}
      />
    </Stack>
  );
}

FormSchemaWithSelectedModel.propTypes = {
  modelToConfigure: PropTypes.string,
  initialValues: PropTypes.object,
  onFormSubmit: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  saveButtonText: PropTypes.string,
  hideButtons: PropTypes.bool,
  onValuesChange: PropTypes.func,
  formSubmitRef: PropTypes.object,
  onErrorChange: PropTypes.func,
};

export default FormSchemaWithSelectedModel;
