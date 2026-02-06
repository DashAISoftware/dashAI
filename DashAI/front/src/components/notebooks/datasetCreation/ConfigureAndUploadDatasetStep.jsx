import { useState, useEffect, useCallback } from "react";
import { Grid, CircularProgress, useTheme } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import Upload from "./Upload";
import { useSnackbar } from "notistack";
import { enqueueDatasetJob as enqueueDatasetRequest } from "../../../api/job";
import { useTourContext } from "../../tour/TourProvider";

import { createDataset } from "../../../api/datasets";
import { useTranslation } from "react-i18next";

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
  const [columnTypes, setColumnTypes] = useState(null);
  const tourContext = useTourContext();

  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["common", "datasets"]);
  const theme = useTheme();

  useEffect(() => {
    if (onPreviewError) {
      onPreviewError(previewError);
    }
  }, [previewError, onPreviewError]);

  useEffect(() => {
    if (previewError) {
      enqueueSnackbar(t("datasets:error.loadingDatasetPreview"), {
        variant: "error",
      });
    }
  }, [previewError, enqueueSnackbar]);

  const submitNewDataset = useCallback(async () => {
    if (!datasetFileToUpload || !datasetFileToUpload.file) {
      enqueueSnackbar(t("datasets:error.noDatasetFileAvailable"), {
        variant: "error",
      });
      return;
    }

    setUploading(true);

    try {
      // Safely read values from the form ref (may be undefined briefly)
      const refValues =
        formSubmitRef && formSubmitRef.current
          ? formSubmitRef.current.values || {}
          : {};
      // Merge values coming from the form schema and the onValuesChange callback
      const params = { ...refValues, ...(formValues || {}) };

      const name = params.name || datasetFileToUpload.file.name;
      params["name"] = name;

      // Ensure dataloader is passed as a string (backend expects the dataloader name)
      let dataloaderName = selectedDataloader;
      if (selectedDataloader && typeof selectedDataloader === "object") {
        dataloaderName =
          selectedDataloader.name || selectedDataloader.display_name || null;
      }
      params["dataloader"] = dataloaderName;

      if (columnTypes) {
        params["inferred_types"] = columnTypes;
      }

      const { file, url } = datasetFileToUpload;

      const data = await createDataset(name);

      try {
        const job = await enqueueDatasetRequest(data.id, file, url, params);
        handleDatasetCreated(data, job);

        if (tourContext?.run) {
          tourContext.nextStep();
        }
      } catch (err) {
        console.error("Error enqueuing dataset job:", err);
        enqueueSnackbar(t("datasets:error.enqueueDatasetJob"), {
          variant: "error",
        });
        backHome();
      }
    } catch (error) {
      console.error("Error creating dataset:", error);
      enqueueSnackbar(t("datasets:error.createDatasetError"), {
        variant: "error",
      });
      backHome();
    } finally {
      setUploading(false);
    }
  }, [
    selectedDataloader,
    datasetFileToUpload,
    columnTypes,
    formSubmitRef,
    handleDatasetCreated,
    backHome,
    enqueueSnackbar,
    tourContext,
  ]);

  const handleFileUpload = (file, url) => {
    setDatasetFileToUpload({ file, url });
  };

  const handleTypesChanged = useCallback((types) => {
    setColumnTypes(types);
  }, []);

  const isFormValid = () => {
    if (!formSubmitRef.current) return false;

    const formik = formSubmitRef.current;
    const hasErrors = formik.errors && Object.keys(formik.errors).length > 0;

    return !hasErrors && !formHasErrors;
  };

  useEffect(() => {
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
          backgroundColor: theme.palette.ui.box,
          border: `1px solid ${theme.palette.ui.border}`,
          padding: 4,
          borderRadius: 2,
        }}
      >
        <Upload
          onFileUpload={handleFileUpload}
          formSubmitRef={formSubmitRef}
          formValues={formValues}
          selectedDataloader={selectedDataloader}
          onPreviewError={setPreviewError}
          onTypesChanged={handleTypesChanged}
        />
      </Grid>

      {/* Form buttons */}
      <Grid sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
        {uploading ? (
          <CircularProgress />
        ) : (
          <FormSchemaButtonGroup
            onCancel={goToPrevStep}
            onFormSubmit={submitNewDataset}
            formik={{
              errors: uploadEnabled
                ? {}
                : { dataset: t("datasets:error.requiredFieldsMissing") },
            }}
            saveButtonText={t("common:upload")}
            backButtonText={t("common:back")}
            dataTour="dataset-step-upload-button"
          />
        )}
      </Grid>
    </Grid>
  );
}
