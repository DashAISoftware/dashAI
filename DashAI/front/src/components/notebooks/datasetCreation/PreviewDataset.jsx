import { useCallback, useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { Box, Button, CircularProgress, Grid, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { previewWithTypes } from "../../../api/datasets";
import PreviewDatasetTable from "./PreviewDatasetTable";

/**
 * This component shows a preview of the dataset before final upload.
 *
 * @param {object} datasetData - Object containing params, file, and url for the dataset
 * @param {function} onChangeDataset - Callback function when the user wants to change the dataset
 * @param {function} onPreviewError - Callback function to notify parent of preview errors
 * @param {function} onTypesChanged - Callback to notify parent when column types change
 */
function PreviewDataset({
  datasetData,
  onChangeDataset,
  onPreviewError,
  onTypesChanged,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [previewData, setPreviewData] = useState(null);
  const [columnTypes, setColumnTypes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const onTypesChangedRef = useRef(onTypesChanged);

  useEffect(() => {
    onTypesChangedRef.current = onTypesChanged;
  }, [onTypesChanged]);

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
          inference_rows: 1000,
          ...params,
        };
        formData.append("params", JSON.stringify(previewParams));

        const result = await previewWithTypes(formData);
        setPreviewData(result);
        setColumnTypes(result.inferred_types);

        if (onTypesChangedRef.current) {
          onTypesChangedRef.current(result.inferred_types);
        }

        setError(null);
      } catch (err) {
        console.error("Error loading preview:", err);
        setError("Failed to load preview");
      } finally {
        setLoading(false);
      }
    };

    loadPreview();
    // Re-run preview when the file changes OR when params change. We stringify params to
    // create a stable dependency so changes to configuration in the right sidebar
    // trigger a new preview request.
  }, [datasetData?.file, JSON.stringify(datasetData?.params || {})]);

  const handleTypeChange = useCallback(
    (typeChanges) => {
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

        if (onTypesChangedRef.current) {
          onTypesChangedRef.current(updatedTypes);
        }

        return updatedTypes;
      });

      enqueueSnackbar("Column types updated successfully", {
        variant: "success",
      });
    },
    [enqueueSnackbar, onTypesChanged],
  );

  return (
    <Grid
      sx={{
        borderRadius: 2,
        boxShadow: "none",
      }}
    >
      <Grid sx={{ p: 4 }}>
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
          <Box
            sx={{
              border: 1,
              borderWidth: 1,
              borderStyle: "dashed",
              borderRadius: 2,
              height: "33vh",
              width: "60%",
              maxWidth: "600px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
              margin: "0 auto",
            }}
          >
            <Typography color="error" variant="h6">
              {error}
            </Typography>
            <Button
              onClick={(e) => {
                e.stopPropagation();
                onChangeDataset(e);
              }}
              sx={{
                position: "absolute",
                top: 8,
                right: 8,
                minWidth: "auto",
                width: 32,
                height: 32,
                borderRadius: "50%",
                padding: 0,
                fontSize: "1.3rem",
                color: "text.secondary",
                "&:hover": {
                  backgroundColor: "ui.hover",
                },
              }}
            >
              ✕
            </Button>
          </Box>
        )}

        {!loading && !error && previewData && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              width: "100%",
            }}
          >
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
                  fontSize: "0.7rem",
                  px: 1.5,
                  py: 0.5,
                  textTransform: "uppercase",
                  minWidth: "auto",
                  flexShrink: 0,
                }}
              >
                Re-upload dataset
              </Button>
            </Box>

            <Box sx={{ width: "100%" }}>
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
  onTypesChanged: PropTypes.func,
};

export default PreviewDataset;
