import { useState, useEffect, useCallback, useRef } from "react";
import { Box, Button, Grid } from "@mui/material";
import Upload from "./Upload";
import { useSnackbar } from "notistack";
import { enqueueDatasetJob as enqueueDatasetRequest } from "../../../api/job";
import { forceRefreshNow } from "../../../utils/jobPoller";
import { useTourContext } from "../../tour/TourProvider";

import { createDataset } from "../../../api/datasets";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

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
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [datasetFileToUpload, setDatasetFileToUpload] = useState(null);
  const [columnTypes, setColumnTypes] = useState(null);
  const [columnRenames, setColumnRenames] = useState({});
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

      if (Object.keys(columnRenames).length > 0) {
        params["column_renames"] = columnRenames;
      }

      const { file, url } = datasetFileToUpload;

      const data = await createDataset(name);

      try {
        const job = await enqueueDatasetRequest(data.id, file, url, params);
        forceRefreshNow();
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
    columnRenames,
    formSubmitRef,
    handleDatasetCreated,
    backHome,
    enqueueSnackbar,
    tourContext,
  ]);

  const handleFileUpload = (file, url) => {
    setDatasetFileToUpload({ file, url });
    setPreviewLoaded(false);
  };

  const handlePreviewLoaded = () => {
    setPreviewLoaded(true);
  };

  const handleTypesChanged = useCallback((types) => {
    setColumnTypes(types);
  }, []);

  const handleColumnRename = useCallback((oldName, newName) => {
    setColumnRenames((prev) => ({
      ...prev,
      [oldName]: newName,
    }));
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
      previewLoaded &&
      isFormValid()
    ) {
      setUploadEnabled(true);
    } else {
      setUploadEnabled(false);
    }
  }, [
    datasetFileToUpload,
    previewError,
    previewLoaded,
    formHasErrors,
    formValues,
  ]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        flex: 1,
        minHeight: 0,
      }}
    >
      <Grid
        container
        direction="column"
        justifyContent="flex-start"
        alignItems="stretch"
        spacing={2}
        sx={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          width: "100%",
          backgroundColor: theme.palette.background.box,
          padding: 2,
          borderRadius: 2,
        }}
      >
        <Upload
          onFileUpload={handleFileUpload}
          formSubmitRef={formSubmitRef}
          onColumnRename={handleColumnRename}
          formValues={formValues}
          selectedDataloader={selectedDataloader}
          onPreviewError={setPreviewError}
          onTypesChanged={handleTypesChanged}
          onPreviewLoaded={handlePreviewLoaded}
        />
      </Grid>

      <Box
        sx={{
          mt: 2,
          pt: 2,
          borderTop: 1,
          borderColor: "divider",
          flexShrink: 0,
          display: "flex",
          justifyContent: "flex-end",
          gap: 1,
        }}
      >
        <Button variant="outlined" onClick={goToPrevStep}>
          {t("common:back")}
        </Button>
        <Button
          variant="contained"
          onClick={submitNewDataset}
          disabled={!uploadEnabled}
          data-tour="dataset-step-upload-button"
          loading={uploading}
        >
          {t("common:upload")}
        </Button>
      </Box>
    </Box>
  );
}
