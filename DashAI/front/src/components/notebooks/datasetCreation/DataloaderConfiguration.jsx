import { DialogContentText, Paper, Stack } from "@mui/material";
import PropTypes from "prop-types";
import { useState, useMemo } from "react";
import FormSchema from "../../shared/FormSchema";
import FormSchemaLayout from "../../shared/FormSchemaLayout";
import { generateDatasetName } from "../../../utils/nameGenerator";

/**
 * This component is a form to configure a dataloader
 * @param {string} dataloader - The dataloader to configure
 * @param {function} onSubmit - The function to submit the form
 * @param {object} formSubmitRef - The reference to the form submit function
 * @param {function} setError - The function to set the error state
 * @param {array} existingDatasets - Array of existing datasets to avoid name conflicts
 */
function DataloaderConfiguration({
  dataloader,
  onSubmit,
  formSubmitRef,
  setError,
  existingDatasets = [],
}) {
  const [splitError, setSplitError] = useState(false);

  const { defaultName } = useMemo(
    () => generateDatasetName(existingDatasets),
    [existingDatasets],
  );

  const handleSubmitButtonClick = (values) => {
    onSubmit(values);
    setError(false);
    setSplitError(false);
  };

  return (
    <Paper sx={{ p: 4, height: "100%" }} borderRadius={2}>
      <Stack spacing={3}>
        {/* Form title */}
        <DialogContentText sx={{ alignSelf: "center" }}>
          {dataloader} configuration
        </DialogContentText>

        <FormSchemaLayout>
          <FormSchema
            autoSave
            model={dataloader}
            onFormSubmit={handleSubmitButtonClick}
            formSubmitRef={formSubmitRef}
            setError={setError}
            initialValues={{ name: defaultName }}
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
  existingDatasets: PropTypes.array,
};

export default DataloaderConfiguration;
