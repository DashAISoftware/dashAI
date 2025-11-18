import React, { useCallback, useRef, useState, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  CircularProgress,
  DialogContentText,
  Grid,
  Typography,
} from "@mui/material";

import PreviewDataset from "./PreviewDataset";
/**
 * Renders a drag and drop to upload a file (dataset).
 * The upload (send to API) doesn't happen here, this component just adds the file "uploaded" to the
 * newDataset state in the modal
 * @param {function} onFileUpload function to handle when the user "uploads" a dataset
 * @param {File} initialFile optional initial file to display (when coming back from preview)
 * @param {object} formValues current form values from the configuration form
 * @param {function} onPreviewError callback to notify parent of preview errors
 */
function Upload({
  onFileUpload,
  initialFile = null,
  formValues = {},
  selectedDataloader = null,
  onPreviewError,
}) {
  const [EMPTY, LOADING, LOADED] = [0, 1, 2];
  const [datasetState, setDatasetState] = useState(
    initialFile ? LOADED : EMPTY,
  );
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(initialFile);
  const inputRef = useRef(null);

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

  const handleDeleteDataset = useCallback(() => {
    onFileUpload(null, "");
    setDatasetState(EMPTY);
    setFile(null);
  }, [onFileUpload]);

  // memoize datasetData object so its reference stays stable across renders
  const datasetDataMemo = useMemo(() => {
    console.log(formValues);
    // Build params but remove keys that don't apply to the selected dataloader
    const params = {
      ...formValues,
      inference_rows:
        formValues && formValues.inference_rows != null
          ? formValues.inference_rows
          : 1000,
    };

    return {
      file,
      params,
    };
  }, [file, formValues, selectedDataloader]);

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
            <Box
              sx={{
                width: "100%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <PreviewDataset
                datasetData={datasetDataMemo}
                onChangeDataset={(e) => {
                  e.stopPropagation();
                  handleDeleteDataset();
                }}
                onPreviewError={onPreviewError}
              />
            </Box>
          );
      }
    },
    [handleSelect, datasetDataMemo, onPreviewError, handleDeleteDataset],
  );

  return (
    <Grid container direction="column" rowSpacing={1} sx={{ width: "100%" }}>
      {/* state text */}
      <Grid sx={{ textAlign: "center" }}>
        <DialogContentText>
          {datasetState === EMPTY && "Upload your dataset"}
          {datasetState === LOADING && "Dataset Loading..."}
          {datasetState === LOADED && "Dataset preview"}
          {datasetState === EMPTY && (
            <Typography variant="body2" component="div">
              If your dataset have splits, upload it as a zip file
            </Typography>
          )}
        </DialogContentText>
      </Grid>

      {/* Drag and drop */}
      <Grid sx={{ width: "100%", display: "flex", justifyContent: "center" }}>
        <Box
          sx={{
            ...(datasetState === LOADED
              ? {}
              : {
                  border: 1,
                  borderWidth: 1,
                  borderStyle: "dashed",
                }),
            ...(datasetState === LOADED
              ? { minHeight: "33vh" }
              : { height: "33vh" }),
            width: datasetState === LOADED ? "100%" : "60%",
            maxWidth: datasetState === LOADED ? "100%" : "600px",
            borderRadius: 2,
            cursor: datasetState === EMPTY ? "pointer" : "auto",
            overflow: datasetState === LOADED ? "visible" : "auto",
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
              height: datasetState === LOADED ? "auto" : "100%",
              width: "100%",
              flex: 1,
            }}
          >
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
  selectedDataloader: PropTypes.string,
  onPreviewError: PropTypes.func,
};

export default Upload;
