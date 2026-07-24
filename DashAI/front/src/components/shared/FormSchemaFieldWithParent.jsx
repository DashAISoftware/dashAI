import { Box, MenuItem, Tooltip, IconButton } from "@mui/material";
import PropTypes from "prop-types";
import { Input } from "../configurableObject/Inputs/InputStyles";
import React from "react";
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
import ComponentDownloadControl from "../models/model/ComponentDownloadControl";

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
  const { addProperty, getModelFromCurrentProperty } = useFormSchemaStore();
  const { models, markDownloaded } = useModelParents({
    parent: field.value?.properties.component,
  });
  const { t } = useTranslation(["common"]);

  const selectedComponent = models?.find(
    (model) => model.name === getModelFromCurrentProperty(name),
  );

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
    addProperty({ key: name, label });
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
      {selectedComponent?.metadata?.requires_download && (
        <Box sx={{ mt: 1 }}>
          <ComponentDownloadControl
            component={selectedComponent}
            onStatusChange={(isDownloaded) =>
              markDownloaded(selectedComponent.name, isDownloaded)
            }
          />
        </Box>
      )}
    </FormSchemaFieldCard>
  );
}

FormSchemaFieldWithParent.propTypes = {
  name: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  description: PropTypes.string,
  errorMessage: PropTypes.string,
  field: PropTypes.object.isRequired,
};

export default FormSchemaFieldWithParent;
