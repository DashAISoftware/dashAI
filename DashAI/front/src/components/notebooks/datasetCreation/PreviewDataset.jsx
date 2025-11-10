import { useCallback, useEffect, useState } from "react";
import { Grid, Typography, CircularProgress, Box, Paper } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import { useSnackbar } from "notistack";
import { enqueueDatasetJob as enqueueDatasetRequest } from "../../../api/job";
import { createDataset, previewWithTypes } from "../../../api/datasets";
import PreviewDatasetTable from "./PreviewDatasetTable";

/**
 * This component shows a preview of the dataset before final upload.
 * It contains the Upload button that creates the dataset and enqueues the processing job.
 *
 * @param {object} datasetData - Object containing params, file, and url for the dataset
 * @param {function} goToPrevStep - Function to navigate back to the previous step
 * @param {function} backHome - Function to navigate back to home on error
 * @param {function} handleDatasetCreated - Callback when dataset is successfully created
 */
export default function PreviewDataset({
  datasetData,
  goToPrevStep,
  backHome,
  handleDatasetCreated,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load preview data when component mounts
  useEffect(() => {
    const loadPreview = async () => {
      if (!datasetData) {
        setError("No dataset data available");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const { params, file } = datasetData;

        // Prepare FormData
        const formData = new FormData();
        formData.append("file", file);

        // Add params as JSON string
        const previewParams = {
          separator: params.separator || ",",
          inference_rows: 500,
        };
        formData.append("params", JSON.stringify(previewParams));

        // Call preview endpoint
        const result = await previewWithTypes(formData);
        setPreviewData(result);
        setError(null);
      } catch (err) {
        console.error("Error loading preview:", err);
        setError("Failed to load preview");
        enqueueSnackbar("Error loading dataset preview", {
          variant: "error",
        });
      } finally {
        setLoading(false);
      }
    };

    loadPreview();
  }, [datasetData, enqueueSnackbar]);

  const submitNewDataset = useCallback(async () => {
    if (!datasetData) {
      enqueueSnackbar("No dataset data available", {
        variant: "error",
      });
      return;
    }

    const { params, file, url } = datasetData;
    const name = params.name;

    try {
      const data = await createDataset(name);
      enqueueSnackbar(`Dataset ${data.name} created successfully`, {
        variant: "success",
      });

      try {
        const job = await enqueueDatasetRequest(data.id, file, url, params);
        handleDatasetCreated(data, job);
      } catch {
        enqueueSnackbar("Error when trying to enqueue the dataset job.", {
          variant: "error",
        });
        backHome();
      }
    } catch (error) {
      enqueueSnackbar("Error creating dataset", {
        variant: "error",
      });
      backHome();
    }
  }, [datasetData, enqueueSnackbar, handleDatasetCreated, backHome]);

  return (
    <Paper
      sx={{
        bgcolor: "#212121",
        borderRadius: 2,
        boxShadow: "none",
        p: 2,
      }}
    >
      <Grid sx={{ p: 4 }}>
        {/* Preview content */}
        {loading && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: "300px",
            }}
          >
            <CircularProgress />
          </Box>
        )}

        {error && !loading && (
          <Box sx={{ textAlign: "center", p: 4 }}>
            <Typography color="error">{error}</Typography>
          </Box>
        )}

        {!loading && !error && previewData && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Showing {previewData.sample.length} of{" "}
              {previewData.preview_row_count} rows analyzed for type inference
            </Typography>
            <PreviewDatasetTable
              rows={previewData.sample}
              columnTypes={previewData.inferred_types}
            />
          </Box>
        )}

        {/* Form buttons */}
        <Grid sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
          <FormSchemaButtonGroup
            onCancel={goToPrevStep}
            onFormSubmit={submitNewDataset}
            formik={{
              errors: {},
            }}
            saveButtonText="Upload"
            backButtonText="Back"
          />
        </Grid>
      </Grid>
    </Paper>
  );
}
