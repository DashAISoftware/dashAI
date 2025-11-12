import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  CircularProgress,
  DialogContentText,
  Grid,
  IconButton,
  Typography,
} from "@mui/material";

import ClearIcon from "@mui/icons-material/Clear";
import { useSnackbar } from "notistack";
import PreviewDatasetTable from "./PreviewDatasetTable";
import { previewWithTypes } from "../../../api/datasets";
/**
 * Renders a drag and drop to upload a file (dataset).
 * The upload (send to API) doesn't happen here, this component just adds the file "uploaded" to the
 * newDataset state in the modal
 * @param {function} onFileUpload function to handle when the user "uploads" a dataset
 * @param {File} initialFile optional initial file to display (when coming back from preview)
 * @param {object} formSubmitRef reference to the form submit function
 * @param {object} formValues current form values from the configuration form
 */
function Upload({
  onFileUpload,
  initialFile = null,
  formSubmitRef = null,
  formValues = {},
}) {
  const [EMPTY, LOADING, LOADED] = [0, 1, 2];
  const [datasetState, setDatasetState] = useState(
    initialFile ? LOADED : EMPTY,
  );
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(initialFile);
  const inputRef = useRef(null);

  const { enqueueSnackbar } = useSnackbar();

  const uploadDataset = async (file) => {
    setDatasetState(LOADING);
    const url = "";
    onFileUpload(file, url);
    setDatasetState(LOADED);
    setFile(file);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (datasetState === EMPTY) {
      if (e.type === "dragenter" || e.type === "dragover") {
        setDragActive(true);
      } else if (e.type === "dragleave") {
        setDragActive(false);
      }
    }
  };

  const handleSelect = (e) => {
    if (datasetState === EMPTY) {
      uploadDataset(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (datasetState === EMPTY) {
      setDragActive(false);
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        uploadDataset(e.dataTransfer.files[0]);
      }
    }
  };

  const handleButtonClick = () => {
    inputRef.current.click();
  };

  const handleDeleteDataset = () => {
    onFileUpload(null, "");
    setDatasetState(EMPTY);
    setFile(null);
  };

  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [previewData, setPreviewData] = useState(null);

  useEffect(() => {
    const loadPreview = async () => {
      if (!file) {
        setPreviewData(null);
        return;
      }

      try {
        setLoadingPreview(true);
        setPreviewError(null);

        // Prepare FormData
        const formData = new FormData();
        formData.append("file", file);

        // Add params as JSON string
        const previewParams = {
          inference_rows: 500,
          ...formValues,
        };
        formData.append("params", JSON.stringify(previewParams));

        // Call preview endpoint
        const result = await previewWithTypes(formData);
        setPreviewData(result);
      } catch (err) {
        console.error("Error loading preview:", err);
        setPreviewError("Failed to load preview");
        enqueueSnackbar("Error loading dataset preview", {
          variant: "error",
        });
      } finally {
        setLoadingPreview(false);
      }
    };

    loadPreview();
  }, [file, formValues, enqueueSnackbar]);

  // renders content inside the drag and drop component depending on the state of the dataset
  const stateContent = useCallback(
    (state) => {
      switch (state) {
        case EMPTY:
          return (
            <React.Fragment>
              <Grid>
                <input
                  type="file"
                  ref={inputRef}
                  style={{ display: "none" }}
                  onChange={handleSelect}
                />
              </Grid>
              {dragActive ? (
                <Grid>
                  <Typography variant="subtitle1">
                    Drop the files here ...
                  </Typography>
                </Grid>
              ) : (
                <React.Fragment>
                  <Grid>
                    <Typography variant="subtitle1">
                      Drag and drop a file here, or
                    </Typography>
                  </Grid>
                  <Grid>
                    <Button variant="contained">Upload a file</Button>
                  </Grid>
                </React.Fragment>
              )}
            </React.Fragment>
          );

        case LOADING:
          return <CircularProgress color="inherit" />;

        case LOADED:
          return (
            <React.Fragment>
              {loadingPreview ? (
                <React.Fragment>
                  <Typography>Loading preview...</Typography>
                  <CircularProgress color="inherit" />
                </React.Fragment>
              ) : previewError ? (
                <Box sx={{ textAlign: "center", p: 2 }}>
                  <Typography color="error">{previewError}</Typography>
                </Box>
              ) : (
                previewData && (
                  <Box sx={{ overflowX: "scroll", width: "100%" }}>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mb: 2, textAlign: "center" }}
                    >
                      Showing {previewData.sample.length} of{" "}
                      {previewData.preview_row_count} rows analyzed for type
                      inference
                    </Typography>
                    <PreviewDatasetTable
                      rows={previewData.sample}
                      columnTypes={previewData.inferred_types}
                    />
                  </Box>
                )
              )}
            </React.Fragment>
          );
      }
    },
    [handleSelect, loadingPreview, previewError, previewData],
  );

  return (
    <Grid container direction="column" rowSpacing={3} sx={{ width: "100%" }}>
      {/* state text */}
      <Grid sx={{ textAlign: "center" }}>
        <DialogContentText>
          {datasetState === EMPTY && "Upload your dataset"}
          {datasetState === LOADING && "Loading..."}
          {datasetState === LOADED && "Loaded"}
          {datasetState === EMPTY && (
            <Typography variant="body2" component="div">
              If your dataset have splits, upload it as a zip file
            </Typography>
          )}
        </DialogContentText>
      </Grid>

      {/* Drag and drop */}
      <Grid sx={{ width: "100%" }}>
        <Box
          sx={{
            ...(datasetState === LOADED && !loadingPreview
              ? {}
              : {
                  border: 1,
                  borderWidth: 1,
                  borderStyle: "dashed",
                }),
            ...(datasetState === LOADED && !loadingPreview
              ? { minHeight: "33vh" }
              : { height: "33vh" }),
            width: "100%",
            borderRadius: 2,
            cursor: datasetState === EMPTY ? "pointer" : "auto",
            overflow:
              datasetState === LOADED && !loadingPreview ? "visible" : "auto",
            position: "relative",
            display: "flex",
          }}
          // blocks the upload of a new file if the file state is not empty
          onClick={datasetState === EMPTY ? handleButtonClick : null}
          onDragEnter={datasetState === EMPTY ? handleDrag : null}
          onDragLeave={datasetState === EMPTY ? handleDrag : null}
          onDragOver={datasetState === EMPTY ? handleDrag : null}
          onDrop={datasetState === EMPTY ? handleDrop : null}
        >
          <Grid
            container
            rowSpacing={1}
            direction="column"
            alignItems="center"
            justifyContent="center"
            sx={{
              height:
                datasetState === LOADED && !loadingPreview ? "auto" : "100%",
              width: "100%",
              flex: 1,
            }}
          >
            {/* delete uploaded dataset button */}
            {datasetState === LOADED && (
              <Grid sx={{ position: "absolute", right: 0, top: 0, zIndex: 1 }}>
                <IconButton onClick={handleDeleteDataset}>
                  <ClearIcon />
                </IconButton>
              </Grid>
            )}

            {/* Content inside the drag and drop that depends on the state */}
            {stateContent(datasetState)}
          </Grid>
        </Box>
      </Grid>
    </Grid>
  );
}

Upload.propTypes = {
  onFileUpload: PropTypes.func.isRequired,
  initialFile: PropTypes.object,
  formSubmitRef: PropTypes.object,
  formValues: PropTypes.object,
};

export default Upload;
