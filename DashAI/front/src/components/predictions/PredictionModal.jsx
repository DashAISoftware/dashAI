import React, { useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  ButtonGroup,
  Stepper,
  Step,
  StepButton,
  Grid,
  Typography,
  IconButton,
} from "@mui/material";
import PropTypes from "prop-types";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useSnackbar } from "notistack";

import SelectModelStep from "./SelectModelStep";
import SelectDatasetStep from "./SelectDatasetStep";
import { enqueuePredictionJob, startJobQueue } from "../../api/job";

function PredictionModal({ open, onClose, updatePredictions }) {
  const theme = useTheme();
  const matches = useMediaQuery(theme.breakpoints.down("md"));
  const screenSm = useMediaQuery(theme.breakpoints.down("sm"));
  const { enqueueSnackbar } = useSnackbar();

  const [activeStep, setActiveStep] = useState(0);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [predictName, setPredictName] = useState("");
  const [trainDataset, setTrainDataset] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const steps = ["Select Model", "Select Dataset"];

  const resetModal = () => {
    setActiveStep(0);
    setSelectedModelId(null);
    setSelectedDatasetId(null);
    setNextEnabled(false);
    setPredictName("");
    setTrainDataset(null);
    setIsSubmitting(false);
  };

  const handleCloseDialog = () => {
    resetModal();
    onClose();
  };

  const handleStepButton = (stepIndex) => () => {
    setActiveStep(stepIndex);
  };

  const handleBackButton = () => {
    if (activeStep === 0) {
      handleCloseDialog();
    } else {
      setActiveStep(activeStep - 1);
    }
  };

  const handleNextButton = () => {
    if (activeStep === steps.length - 1) {
      submitPredictionJob();
      return;
    }

    setActiveStep((prevStep) => prevStep + 1);
    setNextEnabled(false);
  };

  const handlePredictNameInput = (name) => {
    setPredictName(name);
  };

  const submitPredictionJob = async () => {
    if (isSubmitting) return;

    setIsSubmitting(true);

    try {
      enqueueSnackbar("Starting prediction job...", {
        autoHideDuration: 2000,
        variant: "success",
      });

      handleCloseDialog();

      const response = await enqueuePredictionJob(
        selectedModelId,
        selectedDatasetId,
        predictName,
      );

      console.log("Prediction job response:", response);
      console.log("Prediction job id:", response.id);
      if (response?.id) {
        enqueueSnackbar("Prediction job enqueued successfully", {
          autoHideDuration: 2000,
          variant: "success",
        });
      } else {
        enqueueSnackbar("Unexpected response format from the server", {
          autoHideDuration: 2000,
          variant: "warning",
        });
      }

      updatePredictions();

      await startJobQueue();
    } catch (error) {
      console.error("Error submitting prediction job:", error);
      if (error.response) {
        enqueueSnackbar(
          `Error: ${error.response.data?.detail || "Unknown error"}`,
          { variant: "error" },
        );
      } else if (error.request) {
        enqueueSnackbar(
          "No response from the server. Please try again later.",
          {
            variant: "error",
          },
        );
      } else {
        enqueueSnackbar("An unexpected error occurred. Please try again.", {
          variant: "error",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      fullScreen={screenSm}
      fullWidth
      maxWidth={"lg"}
      onClose={handleCloseDialog}
      aria-labelledby="new-predict-dialog-title"
      aria-describedby="new-predict-dialog-description"
      scroll="paper"
      PaperProps={{
        sx: { minHeight: "80vh" },
      }}
    >
      <DialogTitle>
        <Grid container direction={"row"} alignItems={"center"}>
          <Grid item xs={12} md={3}>
            <Grid
              container
              direction="row"
              alignItems="center"
              justifyContent="space-between"
            >
              <Grid item xs={1}>
                <IconButton
                  edge="start"
                  color="inherit"
                  onClick={handleCloseDialog}
                  sx={{ display: { xs: "flex", sm: "none" } }}
                >
                  <CloseIcon />
                </IconButton>
              </Grid>
              <Grid item xs={11}>
                <Typography
                  variant="h6"
                  component="h3"
                  align={matches ? "center" : "left"}
                  sx={{ mb: { sm: 2, md: 0 } }}
                >
                  Create a New Prediction
                </Typography>
              </Grid>
            </Grid>
          </Grid>
          <Grid item xs={12} md={9}>
            <Stepper
              nonLinear
              activeStep={activeStep}
              sx={{ maxWidth: "100%" }}
            >
              {steps.map((step, index) => (
                <Step
                  key={`${step}`}
                  completed={activeStep > index}
                  disabled={activeStep < index}
                >
                  <StepButton color="inherit" onClick={handleStepButton(index)}>
                    {step}
                  </StepButton>
                </Step>
              ))}
            </Stepper>
          </Grid>
        </Grid>
      </DialogTitle>

      <DialogContent dividers>
        {activeStep === 0 && (
          <SelectModelStep
            setSelectedModelId={setSelectedModelId}
            setNextEnabled={setNextEnabled}
            onPredictNameInput={handlePredictNameInput}
            setTrainDataset={setTrainDataset}
          />
        )}
        {activeStep === 1 && (
          <SelectDatasetStep
            setSelectedDatasetId={setSelectedDatasetId}
            setNextEnabled={setNextEnabled}
            trainDataset={trainDataset}
          />
        )}
      </DialogContent>

      <DialogActions>
        <ButtonGroup size="large">
          <Button onClick={handleBackButton}>
            {activeStep === 0 ? "Close" : "Back"}
          </Button>
          <Button
            onClick={handleNextButton}
            autoFocus
            variant="contained"
            color="primary"
            disabled={!nextEnabled || isSubmitting}
          >
            {activeStep === 1
              ? isSubmitting
                ? "Submitting..."
                : "Save"
              : "Next"}
          </Button>
        </ButtonGroup>
      </DialogActions>
    </Dialog>
  );
}

PredictionModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  updatePredictions: PropTypes.func.isRequired,
};

export default PredictionModal;
