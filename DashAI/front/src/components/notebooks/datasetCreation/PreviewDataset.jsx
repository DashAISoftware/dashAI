import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, Button, CircularProgress, Grid, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { previewWithTypes } from "../../../api/datasets";
import PreviewDatasetTable from "./PreviewDatasetTable";

/**
 * This component shows a preview of the dataset before final upload.
 * It contains the Upload button that creates the dataset and enqueues the processing job.
 *
 * @param {object} datasetData - Object containing params, file, and url for the dataset
 * @param {function} onChangeDataset - Callback function when the user wants to change the dataset
 * @param {function} onPreviewError - Callback function to notify parent of preview errors
 */
function PreviewDataset({ datasetData, onChangeDataset, onPreviewError }) {
  const { enqueueSnackbar } = useSnackbar();
  const [previewData, setPreviewData] = useState(null);
  const [columnTypes, setColumnTypes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Notify parent about preview errors
  useEffect(() => {
    if (onPreviewError) {
      onPreviewError(!!error);
    }
  }, [error, onPreviewError]);

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

  return (
    <Grid
      sx={{
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
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              height: "100%",
              maxHeight: "50vh",
            }}
          >
            {/* Header - Fixed */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 2,
                mb: 2,
                flexShrink: 0,
              }}
            >
              <Typography variant="body2" color="text.secondary">
                Showing {previewData.sample.length} of{" "}
                {previewData.preview_row_count} rows analyzed for type
                inference.
                <br />
                You can change column types by clicking on the dropdown in each
                column header.
              </Typography>

              <Button
                variant="contained"
                size="small"
                onClick={onChangeDataset}
                sx={{
                  lineHeight: "1rem",
                  padding: "0.5rem",
                  textTransform: "uppercase",
                  flexShrink: 0,
                }}
              >
                Change Dataset
              </Button>
            </Box>

            {/* Table - Scrollable */}
            <Box
              sx={{
                flex: 1,
                overflow: "auto",
                minHeight: 0,
              }}
            >
              <PreviewDatasetTable
                rows={previewData.sample}
                columnTypes={columnTypes}
                file={datasetData.file}
                params={datasetData.params}
                onTypeChange={handleTypeChange}
              />
            </Box>
          </Box>
        )}
      </Grid>
    </Grid>
  );
}

PreviewDataset.propTypes = {
  datasetData: PropTypes.object,
  onChangeDataset: PropTypes.func,
  onPreviewError: PropTypes.func,
};

export default PreviewDataset;
