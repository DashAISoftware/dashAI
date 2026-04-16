import ModeEditIcon from "@mui/icons-material/ModeEdit";
import { Box, Chip, IconButton, MenuItem, Tooltip } from "@mui/material";
import PropTypes from "prop-types";
import { Input } from "../configurableObject/Inputs/InputStyles";
import React, { useState } from "react";
import { useFormSchemaStore } from "../../contexts/schema";
import FormTooltip from "../configurableObject/FormTooltip";
import TextWithOptions from "./TextWithOptions";
import FormSchemaDialog from "./FormSchemaDialog";
import FormSchema from "./FormSchema";
import useSchema from "../../hooks/useSchema";
import {
  formattedModel,
  formattedSubform,
  generateYupSchema,
  getModelFromSubform,
} from "../../utils/schema";
import useModelParents from "../../hooks/useModelParents";
import { Settings } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

/**
 * This component is a subform for the form schema
 * @param {string} name - The name of the subform
 * @param {string} label - The label of the subform
 * @param {string} description - The description of the subform
 * @param {string} errorMessage - The error message of the subform
 * @param {object} children - The children of the subform
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
  const { models } = useModelParents({
    parent: field.value?.properties.component,
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
    const model = models?.find((model) => model.name === event.target.value);
    const { initialValues } = generateYupSchema(
      await formattedModel(model?.schema),
    );

    field.onChange(
      formattedSubform({
        parent: field.value?.properties.component,
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

  return (
    <Box sx={{ display: "flex", alignItems: "center", pb: 3 }}>
      <Input
        select
        label={label}
        value={getModelFromCurrentProperty(name)}
        onChange={handleOnChange}
      >
        {models?.map((model, index) => (
          <MenuItem key={index} value={model.name}>
            {model.name}
          </MenuItem>
        ))}
      </Input>
      <Tooltip title={t("common:configureSubmodel")}>
        <IconButton onClick={handleClick}>
          <Settings />
        </IconButton>
      </Tooltip>
      <FormTooltip
        contentStr={errorMessage ?? description}
        error={Boolean(errorMessage)}
      />
    </Box>
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
