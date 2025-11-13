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
  const [columnTypes, setColumnTypes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

        const formData = new FormData();
        formData.append("file", file);

        const previewParams = {
          separator: params.separator || ",",
          header: params.header,
          encoding: params.encoding,
          inference_rows: 1000,
        };
        formData.append("params", JSON.stringify(previewParams));

        const result = await previewWithTypes(formData);
        setPreviewData(result);
        setColumnTypes(result.inferred_types);
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

  // Handler cuando el usuario cambia tipos de columnas
  const handleTypeChange = useCallback(
    (typeChanges) => {
      // typeChanges es un objeto: { columnName: { current_type, new_type, new_dtype } }
      setColumnTypes((prevTypes) => {
        const updatedTypes = { ...prevTypes };

        Object.keys(typeChanges).forEach((columnName) => {
          const change = typeChanges[columnName];
          updatedTypes[columnName] = {
            ...updatedTypes[columnName],
            type: change.new_type,
            dtype: change.new_dtype,
          };
        });

        return updatedTypes;
      });

      enqueueSnackbar("Column types updated successfully", {
        variant: "success",
      });
    },
    [enqueueSnackbar],
  );

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
        const enrichedParams = {
          ...params,
          inferred_types: columnTypes,
        };

        const job = await enqueueDatasetRequest(
          data.id,
          file,
          url,
          enrichedParams,
        );
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
  }, [
    datasetData,
    columnTypes,
    enqueueSnackbar,
    handleDatasetCreated,
    backHome,
  ]);

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
              {previewData.preview_row_count} rows analyzed for type inference.
              <br />
              You can change column types by clicking on the dropdown in each
              column header.
            </Typography>
            <PreviewDatasetTable
              rows={previewData.sample}
              columnTypes={columnTypes}
              file={datasetData.file}
              params={datasetData.params}
              onTypeChange={handleTypeChange}
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
