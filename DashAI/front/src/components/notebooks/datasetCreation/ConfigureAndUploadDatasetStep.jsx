import { useState, useEffect, useRef, useCallback } from "react";
import { Grid, CircularProgress } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import Upload from "./Upload";
import { useSnackbar } from "notistack";
import DataloaderConfiguration from "./DataloaderConfiguration";
import { createDataset } from "../../../api/datasets";
import { enqueueDatasetJob as enqueueDatasetRequest } from "../../../api/job";

/**
 * This component combines in a single step the process of uploading a file and configuring the dataloader parameters.
 * It uploads the dataset directly to the API.
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
  const [uploadEnabled, setUploadEnabled] = useState(false);
  const [formValues, setFormValues] = useState({});
  const [uploading, setUploading] = useState(false);

  const [datasetFileToUpload, setDatasetFileToUpload] = useState(null);

  const formSubmitRef = useRef(null);
  const { enqueueSnackbar } = useSnackbar();

  const submitNewDataset = useCallback(async () => {
    if (!datasetFileToUpload || !datasetFileToUpload.file) {
      enqueueSnackbar("No dataset file available", {
        variant: "error",
      });
      return;
    }

    setUploading(true);

    try {
      const params = formSubmitRef.current.values;
      const name = params.name || datasetFileToUpload.file.name;

      params["name"] = name;
      params["dataloader"] = selectedDataloader;

      const { file, url } = datasetFileToUpload;

      // Create dataset
      const data = await createDataset(name);
      enqueueSnackbar(`Dataset ${data.name} created successfully`, {
        variant: "success",
      });

      try {
        // Enqueue dataset job
        const job = await enqueueDatasetRequest(data.id, file, url, params);
        handleDatasetCreated(data, job);
      } catch {
        enqueueSnackbar("Error when trying to enqueue the dataset job.", {
          variant: "error",
        });
        backHome();
      }
    } catch (error) {
      console.error("Error creating dataset:", error);
      enqueueSnackbar("Error creating dataset", {
        variant: "error",
      });
      backHome();
    } finally {
      setUploading(false);
    }
  }, [
    selectedDataloader,
    datasetFileToUpload,
    formSubmitRef,
    handleDatasetCreated,
    backHome,
    enqueueSnackbar,
  ]);

  const handleFileUpload = (file, url) => {
    setDatasetFileToUpload({ file, url });
  };

  useEffect(() => {
    if (datasetFileToUpload && datasetFileToUpload.file !== null && !error) {
      setUploadEnabled(true);
    } else {
      setUploadEnabled(false);
    }
  }, [error, datasetFileToUpload]);

  return (
    <Grid sx={{ width: "100%" }}>
      <Grid
        container
        direction="column"
        justifyContent="space-around"
        alignItems="stretch"
        spacing={2}
        sx={{
          width: "100%",
          backgroundColor: "#212121",
          minHeight: "80vh",
          padding: 4,
          borderRadius: 2,
        }}
      >
        <Upload
          onFileUpload={handleFileUpload}
          formSubmitRef={formSubmitRef}
          formValues={formValues}
        />

        <DataloaderConfiguration
          selectedDataloader={selectedDataloader}
          formSubmitRef={formSubmitRef}
          setError={setError}
          existingDatasets={existingDatasets}
          onValuesChange={setFormValues}
        />
      </Grid>

      {/* Form buttons */}
      <Grid sx={{ m: 2, display: "flex", justifyContent: "flex-end" }}>
        {uploading ? (
          <CircularProgress />
        ) : (
          <FormSchemaButtonGroup
            onCancel={goToPrevStep}
            onFormSubmit={submitNewDataset}
            formik={{
              errors: uploadEnabled
                ? {}
                : { dataset: "Required fields missing" },
            }}
            saveButtonText="Upload"
            backButtonText="Back"
          />
        )}
      </Grid>
    </Grid>
  );
}
