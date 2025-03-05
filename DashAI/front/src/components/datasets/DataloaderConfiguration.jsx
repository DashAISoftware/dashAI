import { DialogContentText, Paper, Stack } from "@mui/material";
import PropTypes from "prop-types";
import React, { useState } from "react";
import FormSchema from "../shared/FormSchema";
import FormSchemaLayout from "../shared/FormSchemaLayout";
/**
 * This component is a form to configure a dataloader
 * @param {string} dataloader - The dataloader to configure
 * @param {function} onSubmit - The function to submit the form
 * @param {object} formSubmitRef - The reference to the form submit function
 * @param {function} setError - The function to set the error state
 */
function DataloaderConfiguration({
  dataloader,
  onSubmit,
  formSubmitRef,
  setError,
}) {
  const [splitError, setSplitError] = useState(false);
  const handleSubmitButtonClick = (values) => {
    onSubmit(values);
    setError(false);
    setSplitError(false);
  };

  return (
    <Paper variant="outlined" sx={{ p: 4 }}>
      <Stack spacing={3}>
        {/* Form title */}

        <DialogContentText sx={{ alignSelf: "center" }}>
          {dataloader} configuration
        </DialogContentText>

        <FormSchemaLayout>
          <FormSchema
            autoSave
            model={dataloader}
            onFormSubmit={(values) => {
              handleSubmitButtonClick(values);
            }}
            formSubmitRef={formSubmitRef}
            setError={setError}
          />
        </FormSchemaLayout>
      </Stack>
    </Paper>
  );
}
DataloaderConfiguration.propTypes = {
  dataloader: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }),
  setError: PropTypes.func,
};

export default DataloaderConfiguration;
