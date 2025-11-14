import { useState, useEffect, useCallback } from "react";
import { Grid, CircularProgress } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import Upload from "./Upload";
import { useSnackbar } from "notistack";
import { createDataset } from "../../../api/datasets";
import { enqueueDatasetJob as enqueueDatasetRequest } from "../../../api/job";

/**
 * This component handles the file upload process for dataset creation.
 * The dataloader configuration is now handled in the right sidebar (DataloaderConfigBar).
 *
 * @param {string} selectedDataloader - The dataloader type to configure
 * @param {function} goToPrevStep - Function to navigate back to the previous step in the dataset creation flow.
 * @param {function} backHome - Function to navigate back to the home/initial state, typically called on error.
 * @param {function} handleDatasetCreated - Callback function called when dataset is successfully created, receives the created dataset data.
 * @param {object} formSubmitRef - The reference to the form submit function from the config bar
 * @param {object} formValues - Current form values from the configuration form
 * @param {function} onPreviewError - Callback to notify parent of preview errors
 * @param {boolean} formHasErrors - Whether the configuration form has validation errors
 */

export default function ConfigureAndUploadDatasetStep({
  selectedDataloader,
  goToPrevStep,
  backHome,
  handleDatasetCreated,
  formSubmitRef,
  formValues,
  onPreviewError,
  formHasErrors,
}) {
  const [uploadEnabled, setUploadEnabled] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewError, setPreviewError] = useState(false);

  const [datasetFileToUpload, setDatasetFileToUpload] = useState(null);

  const { enqueueSnackbar } = useSnackbar();

  // Notify parent about preview errors
  useEffect(() => {
    if (onPreviewError) {
      onPreviewError(previewError);
    }
  }, [previewError, onPreviewError]);

  // Show error notification when preview fails
  useEffect(() => {
    if (previewError) {
      enqueueSnackbar("Error loading dataset preview", {
        variant: "error",
      });
    }
  }, [previewError, enqueueSnackbar]);

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

  // Check if form is valid (no errors) and has required fields
  const isFormValid = () => {
    if (!formSubmitRef.current) return false;

    const formik = formSubmitRef.current;
    const hasErrors = formik.errors && Object.keys(formik.errors).length > 0;
    const isTouched = formik.touched && Object.keys(formik.touched).length > 0;

    // If form has validation errors or the parent reports errors, it's invalid
    return !hasErrors && !formHasErrors;
  };

  useEffect(() => {
    // Enable upload only if:
    // 1. File is uploaded
    // 2. No preview errors
    // 3. Form is valid (no validation errors and all required fields filled)
    if (
      datasetFileToUpload &&
      datasetFileToUpload.file !== null &&
      !previewError &&
      isFormValid()
    ) {
      setUploadEnabled(true);
    } else {
      setUploadEnabled(false);
    }
  }, [datasetFileToUpload, previewError, formHasErrors, formValues]);

  return (
    <Grid sx={{ width: "100%", height: "100%" }}>
      <Grid
        container
        direction="column"
        justifyContent="flex-start"
        alignItems="stretch"
        spacing={2}
        sx={{
          width: "100%",
          backgroundColor: "#212121",
          padding: 4,
          borderRadius: 2,
        }}
      >
        <Upload
          onFileUpload={handleFileUpload}
          formSubmitRef={formSubmitRef}
          formValues={formValues}
          onPreviewError={setPreviewError}
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
