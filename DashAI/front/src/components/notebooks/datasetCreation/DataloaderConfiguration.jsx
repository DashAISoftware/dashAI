import { DialogContentText, Paper, Stack } from "@mui/material";
import PropTypes from "prop-types";
import { useMemo } from "react";
import FormSchema from "../../shared/FormSchema";
import FormSchemaLayout from "../../shared/FormSchemaLayout";
import { generateSequentialName } from "../../../utils/nameGenerator";
import { useTranslation } from "react-i18next";

/**
 * This component is a form to configure a dataloader
 * @param {string} selectedDataloader - The dataloader type to configure
 * @param {object} formSubmitRef - The reference to the form submit function
 * @param {function} setError - The function to set the error state
 * @param {array} existingDatasets - Array of existing datasets to avoid name conflicts
 * @param {function} onValuesChange - Callback function called when form values change
 */
function DataloaderConfiguration({
  selectedDataloader,
  formSubmitRef,
  setError,
  existingDatasets = [],
  onValuesChange,
}) {
  const { t } = useTranslation(["datasets"]);

  const { defaultName } = useMemo(
    () =>
      generateSequentialName({
        base: "Dataset",
        items: existingDatasets,
      }),
    [existingDatasets],
  );

  return (
    <Stack spacing={6}>
      {/* Form title */}
      <DialogContentText sx={{ alignSelf: "center" }}>
        {t("datasets:label.selectedDataloaderConfiguration", {
          dataloader: selectedDataloader,
        })}
      </DialogContentText>

      <FormSchemaLayout>
        <FormSchema
          autoSave
          model={selectedDataloader}
          formSubmitRef={formSubmitRef}
          setError={setError}
          initialValues={{ name: defaultName }}
          onValuesChange={onValuesChange}
        />
      </FormSchemaLayout>
    </Stack>
  );
}

DataloaderConfiguration.propTypes = {
  selectedDataloader: PropTypes.string.isRequired,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }),
  setError: PropTypes.func,
  existingDatasets: PropTypes.array,
  onValuesChange: PropTypes.func,
};

export default DataloaderConfiguration;
