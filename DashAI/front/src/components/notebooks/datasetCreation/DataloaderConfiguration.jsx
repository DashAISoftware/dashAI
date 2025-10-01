import { DialogContentText, Paper, Stack } from "@mui/material";
import PropTypes from "prop-types";
import { useMemo } from "react";
import FormSchema from "../../shared/FormSchema";
import FormSchemaLayout from "../../shared/FormSchemaLayout";
import { generateSequentialName } from "../../../utils/nameGenerator";

/**
 * This component is a form to configure a dataloader
 * @param {string} selectedDataloader - The dataloader type to configure
 * @param {object} formSubmitRef - The reference to the form submit function
 * @param {function} setError - The function to set the error state
 * @param {array} existingDatasets - Array of existing datasets to avoid name conflicts
 */
function DataloaderConfiguration({
  selectedDataloader,
  formSubmitRef,
  setError,
  existingDatasets = [],
}) {
  const { defaultName } = useMemo(
    () =>
      generateSequentialName({
        base: "Dataset",
        items: existingDatasets,
      }),
    [existingDatasets],
  );

  return (
    <Paper sx={{ p: 4, height: "100%" }} borderRadius={2}>
      <Stack spacing={3}>
        {/* Form title */}
        <DialogContentText sx={{ alignSelf: "center" }}>
          {selectedDataloader} configuration
        </DialogContentText>

        <FormSchemaLayout>
          <FormSchema
            autoSave
            model={selectedDataloader}
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
  selectedDataloader: PropTypes.string.isRequired,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }),
  setError: PropTypes.func,
  existingDatasets: PropTypes.array,
};

export default DataloaderConfiguration;
