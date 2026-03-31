import React, { useState, useRef, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Stepper,
  Step,
  DialogActions,
  ButtonGroup,
  Button,
  Grid,
  Typography,
  StepButton,
  Tooltip,
  IconButton,
  Box,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import SelectDataloaderStep from "./SelectDataloaderStep";
import ConfigureAndUploadDataset from "./ConfigureAndUploadDataset";
import { useSnackbar } from "notistack";
import { enqueueDatasetJob as enqueueDatasetRequest } from "../../api/job";
import DatasetPreviewStep from "./DatasetPreviewStep";
import { loadPreview } from "../../api/datasets";

const steps = [
  { name: "selectDataloader", label: "Select a way to upload" },
  { name: "uploadDataset", label: "Configure and upload your dataset" },
  { name: "previewDataset", label: "Preview dataset" },
];

import { inferDataTypes } from "../../api/datasets";
import InferenceMethodSelector from "../custom/InferenceMethodDialog";

const defaultNewDataset = {
  dataloader: "",
  file: null,
  url: "",
  params: {},
};

/**
 * This component renders a modal that takes the user through the process of uploading a new dataset.
 * @param {bool} open true to open the modal, false to close it
 * @param {function} setOpen function to modify the value of open
 * @param {function} updateDatasets function to update the datasets table
 */
function DatasetModal({ open, setOpen, updateDatasets }) {
  const [activeStep, setActiveStep] = useState(0);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [newDataset, setNewDataset] = useState(defaultNewDataset);
  const [uploaded, setUploaded] = useState(false);
  const [columnsSpec, setColumnsSpec] = useState({});
  const [previewData, setPreviewData] = useState({});
  const [loading, setLoading] = useState(false);
  const [inferenceDialogOpen, setInferenceDialogOpen] = useState(false);
  const [selectedInferenceMethods, setSelectedInferenceMethods] = useState([]);
  const formSubmitRef = useRef(null);
  const { enqueueSnackbar } = useSnackbar();

  const handleSubmitNewDataset = async () => {
    try {
      const name =
        newDataset.params.name === null
          ? newDataset.file.name
          : newDataset.params.name;
      newDataset.params["dataloader"] = newDataset.dataloader;
      await enqueueDatasetRequest(newDataset.file, name, newDataset.url, {
        ...newDataset.params,
        schema: columnsSpec,
      });

      enqueueSnackbar("Dataset upload job started", { variant: "success" });
      updateDatasets();
      handleCloseDialog();
    } catch (error) {
      console.error(error);
      setActiveStep(1);
      setNextEnabled(false);
      enqueueSnackbar("Error when trying to upload the dataset.");
    } finally {
      setUploaded(true);
    }
  };

  const handlePreviewDataset = async (file, url) => {
    const formData = new FormData();
    formData.append("file", newDataset.file);
    formData.append("params", JSON.stringify(newDataset.params));

    try {
      const preview = await loadPreview(formData);

      setPreviewData(preview);

      //Save the columns spec to be used in the preview table
      const initialColumnsSpec = {};
      Object.keys(preview.schema).forEach((columnName) => {
        initialColumnsSpec[columnName] = {
          type: preview.schema[columnName].type,
          dtype: preview.schema[columnName].dtype,
        };
      });

      setColumnsSpec(initialColumnsSpec);
      setNextEnabled(true);
    } catch (error) {
      enqueueSnackbar(
        "Error while trying to obtain preview of the uploaded file",
      );
      setActiveStep(1);
      setNextEnabled(false);
      setPreviewData(null);
    }
  };

  const handleColumnRename = (oldName, newName) => {
    setColumnsSpec((prevSpec) => {
      const updatedSpec = { ...prevSpec };

      // Move the spec from old name to new name
      if (updatedSpec[oldName]) {
        updatedSpec[newName] = updatedSpec[oldName];
        delete updatedSpec[oldName];
      }

      return updatedSpec;
    });

    // Also update previewData to reflect the new column name
    setPreviewData((prevData) => {
      if (!prevData || !prevData.schema) return prevData;

      const updatedSchema = { ...prevData.schema };
      if (updatedSchema[oldName]) {
        updatedSchema[newName] = updatedSchema[oldName];
        delete updatedSchema[oldName];
      }

      const updatedSample = prevData.sample.map((row) => {
        const newRow = { ...row };
        if (oldName in newRow) {
          newRow[newName] = newRow[oldName];
          delete newRow[oldName];
        }
        return newRow;
      });

      return {
        ...prevData,
        schema: updatedSchema,
        sample: updatedSample,
      };
    });
  };

  const handleInferDataTypes = async (methods) => {
    setLoading(true);
    const formData = new FormData();
    formData.append("file", newDataset.file);
    formData.append(
      "params",
      JSON.stringify({
        ...newDataset.params,
        methods,
      }),
    );

    try {
      const response = await inferDataTypes(formData);
      const updatedTypes = Object.fromEntries(
        Object.entries(response).map(([key, value]) => [
          key,
          {
            type: value.type,
            dtype: value.dtype,
          },
        ]),
      );

      setColumnsSpec(updatedTypes);
      enqueueSnackbar("Inferred datatypes successfully", {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to infer datatypes", error);
      enqueueSnackbar("Failed to infer datatypes", { variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleCloseDialog = () => {
    setActiveStep(0);
    setNewDataset(defaultNewDataset);
    setUploaded(false);
    setNextEnabled(false);
    setOpen(false);
  };

  const handleStepButton = (stepIndex) => () => {
    setActiveStep(stepIndex);
  };

  const handleNextButton = () => {
    if (activeStep === 0) {
      setActiveStep((prev) => prev + 1);
      setNextEnabled(false);
    } else if (activeStep === 1) {
      handlePreviewDataset();
      setActiveStep(2);
    } else if (activeStep === 2) {
      handleSubmitNewDataset();
    }
  };

  const handleBackButton = () => {
    if (activeStep === 0) {
      handleCloseDialog();
    } else {
      setActiveStep((prev) => prev - 1);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={() => {}}
      disableEscapeKeyDown
      fullWidth
      maxWidth={"lg"}
      scroll="paper"
      slotProps={{
        paper: {
          sx: { minHeight: "80vh" },
        },
      }}
    >
      {/* Title */}
      <DialogTitle id="new-experiment-dialog-title">
        <Grid container direction={"row"} alignItems={"center"} spacing={1}>
          <Grid size={{ xs: 12, md: 3 }}>
            <Typography
              variant="h6"
              component={"h3"}
              sx={{ mb: { sm: 2, md: 0 } }}
            >
              New dataset
            </Typography>
          </Grid>
          <Grid size={{ xs: 12, md: 8 }}>
            <Stepper
              nonLinear
              activeStep={activeStep}
              sx={{ maxWidth: "100%" }}
            >
              {steps.map((step, index) => (
                <Step
                  key={`${step.name}`}
                  completed={activeStep > index}
                  disabled={activeStep < index}
                >
                  <StepButton color="inherit" onClick={handleStepButton(index)}>
                    {step.label}
                  </StepButton>
                </Step>
              ))}
            </Stepper>
          </Grid>
          <Grid
            size={{ xs: 12, md: 1 }}
            display="flex"
            justifyContent="flex-end"
          >
            <IconButton
              onClick={handleCloseDialog}
              sx={{
                position: { xs: "absolute", md: "static" },
                right: { xs: 8, md: "auto" },
                top: { xs: 8, md: "auto" },
              }}
            >
              <CloseIcon />
            </IconButton>
          </Grid>
        </Grid>
      </DialogTitle>
      {/* Main content - steps */}
      <DialogContent dividers>
        {/* Step 1: select dataloader */}
        {activeStep === 0 && (
          <SelectDataloaderStep
            newDataset={newDataset}
            setNewDataset={setNewDataset}
            setNextEnabled={setNextEnabled}
          />
        )}
        {/* Step 2: Configure dataloader and upload file */}
        {activeStep === 1 && (
          <ConfigureAndUploadDataset
            newDataset={newDataset}
            setNewDataset={setNewDataset}
            setNextEnabled={setNextEnabled}
            formSubmitRef={formSubmitRef}
          />
        )}

        {/* Step 3: Preview dataset */}
        {activeStep === 2 && (
          <DatasetPreviewStep
            previewData={previewData}
            newDataset={newDataset}
            setNewDataset={setNewDataset}
            onConfirm={handleSubmitNewDataset}
            setNextEnabled={setNextEnabled}
            columnsSpec={columnsSpec}
            setColumnsSpec={setColumnsSpec}
            onColumnRename={handleColumnRename}
          />
        )}
      </DialogContent>
      {/* Actions - Back and Next */}
      <DialogActions>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            width: "100%",
            alignItems: "center",
          }}
        >
          <Box sx={{ minWidth: "180px" }}>
            {activeStep === 2 && (
              <Tooltip title="The methods used to infer columns datatypes are not perfect and can commit mistakes, please check yourself the types before pressing the Upload button.">
                <Button
                  size="large"
                  variant="contained"
                  color="primary"
                  onClick={() => setInferenceDialogOpen(true)}
                >
                  Infer column Data Types
                </Button>
              </Tooltip>
            )}
          </Box>
          <ButtonGroup size="large">
            <Button onClick={handleBackButton}>
              {activeStep === 0 ? "Close" : "Back"}
            </Button>
            <Button
              onClick={handleNextButton}
              autoFocus
              variant="contained"
              color="primary"
              disabled={!nextEnabled}
            >
              {activeStep === 0
                ? "Next"
                : activeStep === 1
                  ? "Preview"
                  : "Upload"}
            </Button>
          </ButtonGroup>
        </Box>
      </DialogActions>
      <InferenceMethodSelector
        open={inferenceDialogOpen}
        onClose={() => setInferenceDialogOpen(false)}
        onConfirm={(methods) => {
          setSelectedInferenceMethods(methods);
          handleInferDataTypes(methods);
        }}
        defaultSelected={selectedInferenceMethods}
      />
    </Dialog>
  );
}
DatasetModal.propTypes = {
  open: PropTypes.bool.isRequired,
  setOpen: PropTypes.func.isRequired,
  updateDatasets: PropTypes.func.isRequired,
};

export default DatasetModal;
