import { MenuItem, Tooltip, IconButton } from "@mui/material";
import PropTypes from "prop-types";
import { Input } from "../configurableObject/Inputs/InputStyles";
import React, { useState } from "react";
import { useFormSchemaStore } from "../../contexts/schema";
import {
  formattedModel,
  formattedSubform,
  generateYupSchema,
} from "../../utils/schema";
import useModelParents from "../../hooks/useModelParents";
import { Settings } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import FormSchemaFieldCard from "./FormSchemaFieldCard";
import useSchema from "../../hooks/useSchema";

/**
 * Renders a parent-model selector field as a card.
 * The "configure sub-model" icon button lives in the card header.
 * The body contains the model select dropdown.
 */
function FormSchemaFieldWithParent({
  name,
  label,
  field,
  description,
  errorMessage,
}) {
  const { formValues, setFormValues, getModelFromCurrentProperty } =
    useFormSchemaStore();
  const parentComponent =
    field?.value?.properties?.component ?? field?.value?.component ?? null;
  const { models } = useModelParents({
    parent: parentComponent,
  });
  const { t } = useTranslation(["common"]);

  // State for handling the sub-modal
  const [openSubModal, setOpenSubModal] = useState(false);

  // Get the currently selected model name
  const selectedModelName = getModelFromCurrentProperty(name);

  // Get default values for the sub-model
  const { defaultValues: subModelDefaultValues } = useSchema({
    modelName: selectedModelName,
  });

  const handleOnChange = async (event) => {
    if (!parentComponent) {
      return;
    }

    const model = models?.find((model) => model.name === event.target.value);
    if (!model?.schema) {
      return;
    }

    const { initialValues } = generateYupSchema(
      await formattedModel(model?.schema),
    );

    field.onChange(
      formattedSubform({
        parent: parentComponent,
        model: model?.name,
        params: initialValues,
      }),
    );
  };

  const handleClick = () => {
    if (selectedModelName) {
      setOpenSubModal(true);
    }
  };

  // Function to get current values for the sub-model
  const getSubModelInitialValues = () => {
    if (!formValues || !formValues[name]) {
      return subModelDefaultValues || {};
    }

    const fieldValue = formValues[name];
    if (fieldValue?.properties?.params?.comp?.params) {
      return fieldValue.properties.params.comp.params;
    }

    return subModelDefaultValues || {};
  };

  // Handle saving the sub-model configuration
  const handleSubModelSave = (values) => {
    if (formValues && formValues[name]) {
      setFormValues((prevFormValues) => {
        const updatedFormValues = { ...prevFormValues };
        if (updatedFormValues[name]?.properties?.params?.comp) {
          updatedFormValues[name].properties.params.comp.params = values;
        }
        return updatedFormValues;
      });
    }
    setOpenSubModal(false);
  };

  const configureButton = (
    <Tooltip title={t("common:configureSubmodel")}>
      <IconButton size="small" onClick={handleClick}>
        <Settings fontSize="small" />
      </IconButton>
    </Tooltip>
  );

  return (
    <FormSchemaFieldCard
      label={label}
      paramKey={name}
      description={description}
      errorMessage={errorMessage}
      headerRight={configureButton}
    >
      <Input
        select
        value={getModelFromCurrentProperty(name)}
        onChange={handleOnChange}
        size="small"
        sx={{ width: "100%" }}
      >
        {models?.map((model) => (
          <MenuItem key={model.name} value={model.name}>
            {model.name}
          </MenuItem>
        ))}
      </Input>
    </FormSchemaFieldCard>
  );
}

FormSchemaFieldWithParent.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  field: PropTypes.shape({
    value: PropTypes.any,
    onChange: PropTypes.func.isRequired,
    error: PropTypes.any,
  }).isRequired,
  description: PropTypes.string,
  errorMessage: PropTypes.string,
};

export default FormSchemaFieldWithParent;
