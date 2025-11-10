import { useState, useEffect, useRef, useCallback } from "react";
import { Grid } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import Upload from "./Upload";
import { useSnackbar } from "notistack";
import DataloaderConfiguration from "./DataloaderConfiguration";
import { enqueueDatasetJob as enqueueDatasetRequest } from "../../../api/job";
import { useTourContext } from "../../tour/TourProvider";

import { createDataset } from "../../../api/datasets";

/**
 * This component combines in a single step the process of uploading a file and configuring the dataloader parameters.
 * It creates the dataset entry in the database and then enqueues a job to process the uploaded file.
 *
 * @param {string} selectedDataloader - The dataloader type to configure
 * @param {function} goToPrevStep - Function to navigate back to the previous step in the dataset creation flow.
 * @param {function} backHome - Function to navigate back to the home/initial state, typically called on error.
 * @param {function} handleDatasetCreated - Callback function called when dataset is successfully created, receives the created dataset data.
 * @param {array} existingDatasets - Array of existing datasets to avoid name conflicts
 */

export default function ConfigureAndUploadDatasetStep({
  selectedDataloader,
  goToPrevStep,
  backHome,
  handleDatasetCreated,
  existingDatasets = [],
}) {
  const [error, setError] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const [nextEnabled, setNextEnabled] = useState(false);
  const [datasetFileToUpload, setDatasetFileToUpload] = useState(null);
  const tourContext = useTourContext();

  const formSubmitRef = useRef(null);

  useEffect(() => {
    if (formSubmitRef.current && tourContext?.run) {
      setTimeout(() => {
        if (formSubmitRef.current?.setFieldValue) {
          formSubmitRef.current.setFieldValue("name", "Personality Dataset");
        }
      }, 100);
    }
  }, [tourContext, selectedDataloader]);

  const submitNewDataset = useCallback(async () => {
    const params = formSubmitRef.current.values;
    const name = params.name || datasetFileToUpload.file.name;

    params["name"] = name;
    params["dataloader"] = selectedDataloader.name;

    createDataset(name).then(async (data) => {
      enqueueSnackbar(`Dataset ${data.name} created successfully`, {
        variant: "success",
      });
      try {
        const job = await enqueueDatasetRequest(
          data.id,
          datasetFileToUpload.file,
          datasetFileToUpload.url,
          params,
        );
        handleDatasetCreated(data, job);

        if (tourContext?.run) {
          setTimeout(() => {
            tourContext.nextStep();
          }, 500);
        }
      } catch {
        enqueueSnackbar("Error when trying to enqueue the dataset job.", {
          variant: "error",
        });
        backHome();
      }
    });
  }, [
    backHome,
    selectedDataloader,
    datasetFileToUpload,
    enqueueSnackbar,
    handleDatasetCreated,
    formSubmitRef,
    tourContext,
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
          <Upload onFileUpload={handleFileUpload} />
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
          onFormSubmit={submitNewDataset}
          formik={{
            errors: nextEnabled ? {} : { dataset: "Required fields missing" },
          }}
          saveButtonText="Upload"
          backButtonText="Back"
          dataTour="dataset-step-upload-button"
        />
      </Grid>
    </Grid>
  );
}
