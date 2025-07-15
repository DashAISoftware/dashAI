import React, { useState, useRef } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  CircularProgress,
  DialogContentText,
  Grid,
  IconButton,
  Paper,
  Typography,
} from "@mui/material";

import TextSnippetIcon from "@mui/icons-material/TextSnippet";
import ClearIcon from "@mui/icons-material/Clear";

/**
 * Renders a drag and drop to upload a file (dataset).
 * The upload (send to API) doesn't happen here, this component just adds the file "uploaded" to the
 * newDataset state in the modal
 * @param {function} onFileUpload function to handle when the user "uploads" a dataset
 */
function Upload({ onFileUpload, emptyUploadText, multiple = false }) {
  const [EMPTY, LOADING, LOADED] = [0, 1, 2];
  const [datasetState, setDatasetState] = useState(EMPTY);
  const [dragActive, setDragActive] = useState(false);
  const [fileNames, setFileNames] = useState([]);
  const inputRef = useRef(null);

  const uploadDataset = async (files) => {
    const fileArray = Array.isArray(files) ? files : Array.from(files);
    setDatasetState(LOADING);
    const url = "";
    await onFileUpload(fileArray, url);
    setDatasetState(LOADED);
    setFileNames(fileArray.map(f => f.name));
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
      const files = multiple ? e.target.files : [e.target.files[0]];
      uploadDataset(files);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (datasetState === EMPTY) {
      setDragActive(false);
      const files = multiple ? e.dataTransfer.files : [e.dataTransfer.files[0]];
      if (files && files.length > 0) {
        uploadDataset(files);
      }
    }
  };

  const handleButtonClick = () => {
    inputRef.current.click();
  };

  const handleDeleteDataset = () => {
    onFileUpload(null, "");
    setDatasetState(EMPTY);
    setFileNames([]);
  };

  const stateContent = (state) => {
    switch (state) {
      case EMPTY:
        return (
          <>
            <Grid item>
              <input
                type="file"
                ref={inputRef}
                style={{ display: "none" }}
                onChange={handleSelect}
                multiple={multiple}
              />
            </Grid>
            {dragActive ? (
              <Grid item>
                <Typography variant="subtitle1">
                  Drop the file{multiple ? "s" : ""} here.
                </Typography>
              </Grid>
            ) : (
              <>
                <Grid item>
                  <Typography variant="subtitle1">
                    Drag and drop {multiple ? "your files" : "a file"} here, or
                  </Typography>
                </Grid>
                <Grid item>
                  <Button variant="contained">Upload a file</Button>
                </Grid>
              </>
            )}
          </>
        );

      case LOADING:
        return <CircularProgress color="inherit" />;

      case LOADED:
        return (
          <>
            <TextSnippetIcon sx={{ fontSize: "58px" }} />
            <Grid item>
              {fileNames.map((name, index) => (
                <Typography 
                  key={index} 
                  variant="subtitle1"
                  sx={
                    { 
                      color: "gray", 
                      textAlign: "center" 
                    }
                  }>
                  {name}
                </Typography>
              ))}
            </Grid>
          </>
        );
    }
  };

  return (
    <Paper variant="outlined" sx={{ p: 4, height: "100%" }} square>
      <Grid container direction="column" rowSpacing={3}>
        {/* state text */}
        <Grid item sx={{ textAlign: "center" }}>
          <DialogContentText>
            {datasetState === LOADING && "Loading..."}
            {datasetState === LOADED && "Loaded"}
            {/* {datasetState === EMPTY && "Upload your dataset"} */}
            {datasetState === EMPTY &&emptyUploadText}
          </DialogContentText>
        </Grid>

        {/* Drag and drop */}
        <Grid item>
          <Box
            sx={{
              border: 1,
              height: "33vh",
              width: "100%",
              borderRadius: 2,
              cursor: datasetState === EMPTY ? "pointer" : "auto",
              borderWidth: 1,
              borderStyle: "dashed",
              overflow: "auto",
              position: "relative",
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
              sx={{ height: "100%" }}
            >
              {/* delete uploaded dataset button */}
              {datasetState === LOADED && (
                <Grid item sx={{ position: "absolute", right: 0, top: 0 }}>
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
    </Paper>
  );
}

Upload.propTypes = {
  onFileUpload: PropTypes.func.isRequired,
  emptyUploadText: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.node,
  ])
};

export default Upload;
