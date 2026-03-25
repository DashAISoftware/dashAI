import React, { useState } from "react";
import PropTypes from "prop-types";
import { Settings } from "@mui/icons-material";
import FormSchemaDialog from "../../shared/FormSchemaDialog";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import TooltipedCellItem from "../../shared/TooltipedCellItem";

/**
 * Modal to set parameters for a converter
 * @param {Object} props
 * @param {string} props.converterToConfigure - Name of the converter to configure
 * @param {Function} props.updateParameters - Function to update the parameters of the converter
 * @param {Object} props.paramsInitialValues - Initial values of the parameters
 */
const ConverterEditorModal = ({
  converterToConfigure = "",
  updateParameters,
  paramsInitialValues = {},
}) => {
  const [open, setOpen] = useState(false);

  const handleOnSave = (paramsAndValues) => {
    updateParameters(paramsAndValues);
    setOpen(false);
  };

  return (
    <React.Fragment>
      <TooltipedCellItem
        key="edit-button"
        icon={<Settings />}
        label="Set"
        tooltip="Set parameters"
        onClick={() => setOpen(true)}
      />
      <FormSchemaDialog
        modelToConfigure={converterToConfigure}
        open={open}
        setOpen={setOpen}
        onFormSubmit={handleOnSave}
      >
        <FormSchemaWithSelectedModel
          onFormSubmit={handleOnSave}
          modelToConfigure={converterToConfigure}
          initialValues={paramsInitialValues}
          onCancel={() => setOpen(false)}
        />
      </FormSchemaDialog>
    </React.Fragment>
  );
};

ConverterEditorModal.propTypes = {
  converterToConfigure: PropTypes.string,
  updateParameters: PropTypes.func.isRequired,
  paramsInitialValues: PropTypes.objectOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.bool,
      PropTypes.number,
      PropTypes.array,
    ]),
  ),
};

export default ConverterEditorModal;
