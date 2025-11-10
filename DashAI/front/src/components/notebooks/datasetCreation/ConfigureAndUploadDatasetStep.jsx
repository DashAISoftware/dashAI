import { useState, useEffect, useRef, useCallback } from "react";
import { Grid } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import Upload from "./Upload";
import { useSnackbar } from "notistack";
import DataloaderConfiguration from "./DataloaderConfiguration";
import {
  enqueueDatasetJob as enqueueDatasetRequest,
  startJobQueue,
} from "../../../api/job";

import { createDataset } from "../../../api/datasets";

/**
 * This component combines in a single step the process of uploading a file and configuring the dataloader parameters.
 * It prepares the dataset data for preview before final upload.
 *
 * @param {string} selectedDataloader - The dataloader type to configure
 * @param {function} goToNextStep - Function to navigate to the next step (preview).
 * @param {function} goToPrevStep - Function to navigate back to the previous step in the dataset creation flow.
 * @param {function} backHome - Function to navigate back to the home/initial state, typically called on error.
 * @param {function} handleDatasetCreated - Callback function called when dataset is successfully created, receives the created dataset data.
 * @param {array} existingDatasets - Array of existing datasets to avoid name conflicts
 * @param {function} setDatasetData - Function to save dataset data for preview
 * @param {object} initialDatasetData - Previously saved dataset data (for when user goes back from preview)
 */

export default function ConfigureAndUploadDatasetStep({
  selectedDataloader,
  goToNextStep,
  goToPrevStep,
  backHome,
  handleDatasetCreated,
  existingDatasets = [],
  setDatasetData,
  initialDatasetData = null,
}) {
  const [error, setError] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const [nextEnabled, setNextEnabled] = useState(false);

  // Initialize with previous data if available (when coming back from preview)
  const [datasetFileToUpload, setDatasetFileToUpload] = useState(
    initialDatasetData
      ? { file: initialDatasetData.file, url: initialDatasetData.url }
      : null,
  );

  const formSubmitRef = useRef(null);

  const prepareDataForPreview = useCallback(() => {
    const params = formSubmitRef.current.values;
    const name = params.name || datasetFileToUpload.file.name;

    params["name"] = name;
    params["dataloader"] = selectedDataloader;

    // Save data for preview step
    setDatasetData({
      params,
      file: datasetFileToUpload.file,
      url: datasetFileToUpload.url,
    });

    // Go to preview step
    goToNextStep();
  }, [
    selectedDataloader,
    datasetFileToUpload,
    setDatasetData,
    goToNextStep,
    formSubmitRef,
  ]);

  const handleFileUpload = (file, url) => {
    setDatasetFileToUpload({ file, url });
  };

  useEffect(() => {
    if (datasetFileToUpload && datasetFileToUpload.file !== null && !error) {
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [error, datasetFileToUpload]);

  return (
    <Grid sx={{ p: 4 }}>
      <Grid
        container
        direction="row"
        justifyContent="space-around"
        alignItems="stretch"
        spacing={3}
      >
        {/* Upload file */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Upload
            onFileUpload={handleFileUpload}
            initialFile={initialDatasetData?.file}
          />
        </Grid>

        {/* Configure dataloader parameters */}
        <Grid size={{ xs: 12, md: 7 }}>
          <DataloaderConfiguration
            selectedDataloader={selectedDataloader}
            formSubmitRef={formSubmitRef}
            setError={setError}
            existingDatasets={existingDatasets}
          />
        </Grid>
      </Grid>

      {/* Form buttons */}
      <Grid sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
        <FormSchemaButtonGroup
          onCancel={goToPrevStep}
          onFormSubmit={prepareDataForPreview}
          formik={{
            errors: nextEnabled ? {} : { dataset: "Required fields missing" },
          }}
          saveButtonText="Next"
          backButtonText="Back"
        />
      </Grid>
    </Grid>
  );
}
