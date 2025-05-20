import React, { useState } from "react";
import PropTypes from "prop-types";

import SettingsIcon from "@mui/icons-material/Settings";

import FormSchemaDialog from "../../shared/FormSchemaDialog";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import TooltipedCellItem from "../../shared/TooltipedCellItem";

/**
 * Dialog to edit the parameters of a explorer.
 * @param {Object} props
 * @param {String} props.componentToConfigure - explorationType to configure
 * @param {Function} props.updateParameters - Function to update the parameters
 * @param {Object} props.paramsInitialValues - Initial values of the parameters
 */
function EditParametersDialog({
  componentToConfigure,
  updateParameters,
  paramsInitialValues,
}) {
  const [open, setOpen] = useState(false);

  return (
    <React.Fragment>
      <TooltipedCellItem
        key="edit-parameters-button"
        icon={<SettingsIcon />}
        label="Edit Parameters"
        tooltip={`Configure parameters`}
        onClick={() => setOpen(true)}
      />

      {open && (
        <FormSchemaDialog
          modelToConfigure={componentToConfigure}
          open={open}
          setOpen={setOpen}
          onFormSubmit={(values) => {
            updateParameters(values);
            setOpen(false);
          }}
        >
          <FormSchemaWithSelectedModel
            onFormSubmit={(values) => {
              updateParameters(values);
              setOpen(false);
            }}
            modelToConfigure={componentToConfigure}
            initialValues={paramsInitialValues}
            onCancel={() => setOpen(false)}
          />
        </FormSchemaDialog>
      )}
    </React.Fragment>
  );
}

EditParametersDialog.propTypes = {
  componentToConfigure: PropTypes.string.isRequired,
  updateParameters: PropTypes.func.isRequired,
  paramsInitialValues: PropTypes.objectOf(
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.bool,
      PropTypes.number,
      PropTypes.object,
    ]),
  ),
};

export default EditParametersDialog;
