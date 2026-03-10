import React, { useEffect } from "react";
import { Paper, Grid, Typography, CircularProgress } from "@mui/material";
import PropTypes from "prop-types";
import DatasetPreviewTable from "./DatasetPreviewTable";

function DatasetPreviewStep({
  previewData, // preview data from the API
  setNextEnabled, // function to enable or disable the "Next" button in the modal
  columnsSpec, // columns specification for the dataset
  setColumnsSpec, // function to set the columns specification
}) {
  useEffect(() => {
    if (previewData && Object.keys(previewData).length > 0) {
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [previewData, setNextEnabled]);
  return (
    <Paper
      variant="outlined"
      sx={{ p: 4, maxHeight: "55vh", overflow: "auto" }}
    >
      <Grid container direction={"column"} alignItems={"center"}>
        <Grid item>
          <Typography variant="subtitle1">Dataset Summary</Typography>
          <Typography
            item
            variant="caption"
            component="h3"
            sx={{ mb: 2, color: "grey" }}
          >
            Summary of the recently uploaded dataset with predefined column
            types. You can modify the type by selecting a different value.
          </Typography>
        </Grid>
        <Grid item>
          {previewData ? (
            <>
              <DatasetPreviewTable
                previewData={previewData}
                isEditable={true}
                columnsSpec={columnsSpec}
                setColumnsSpec={setColumnsSpec}
              />
            </>
          ) : (
            <CircularProgress />
          )}
        </Grid>
      </Grid>
    </Paper>
  );
}
DatasetPreviewStep.propTypes = {
  previewData: PropTypes.object.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
  datasetUploaded: PropTypes.bool,
  columnsSpec: PropTypes.object.isRequired,
  setColumnsSpec: PropTypes.func.isRequired,
};
export default DatasetPreviewStep;
