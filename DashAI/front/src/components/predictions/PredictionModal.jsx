import { useState, useMemo, useEffect } from "react";
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
import { renderStep } from "./renderStep";

import { enqueuePredictionJob, startJobQueue } from "../../api/job";
import { generateSequentialName } from "../../utils/nameGenerator";

function PredictionModal({
  open,
  onClose,
  updatePredictions,
  preselectedModelId,
  setPreselectedModelId,
  preselectedTrainedDatasetId,
  setPreselectedTrainedDatasetId,
  existingPredictions = [],
}) {
  const theme = useTheme();
  const matches = useMediaQuery(theme.breakpoints.down("md"));
  const screenSm = useMediaQuery(theme.breakpoints.down("sm"));
  const { enqueueSnackbar } = useSnackbar();

  const [activeStep, setActiveStep] = useState(0);
  const [selectedModelId, setSelectedModelId] = useState(preselectedModelId);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [manualInputData, setManualInputData] = useState(null);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [predictName, setPredictName] = useState("");
  const [trainDataset, setTrainDataset] = useState(preselectedTrainedDatasetId);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { defaultName } = useMemo(
    () =>
      generateSequentialName({
        base: "Prediction",
        items: existingPredictions,
        getName: (prediction) => prediction.pred_name,
        allowExtension: true,
      }),
    [existingPredictions],
  );

  const steps = [
    ...(preselectedModelId
      ? []
      : [{ name: "selectModel", label: "Select Model" }]),
    { name: "selectDataset", label: "Select Dataset" },
  ];

  const resetModal = () => {
    setActiveStep(0);
    setSelectedModelId(null);
    setPreselectedModelId(null);
    setPreselectedTrainedDatasetId(null);
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

      // Use generated name if user didn't provide one
      const finalPredictionName =
        predictName.trim() === "" ? defaultName : predictName.trim();

      const response = await enqueuePredictionJob(
        selectedModelId,
        selectedDatasetId,
        finalPredictionName,
      );

      console.log("Prediction job response:", response);
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
      slotProps={{
        paper: {
          sx: { minHeight: "80vh" },
        },
      }}
    >
      <DialogTitle>
        <Grid container direction={"row"} alignItems={"center"}>
          <Grid size={{ xs: 12, md: 3 }}>
            <Grid
              container
              direction="row"
              alignItems="center"
              justifyContent="space-between"
            >
              <Grid size={{ xs: 1 }}>
                <IconButton
                  edge="start"
                  color="inherit"
                  onClick={handleCloseDialog}
                  sx={{ display: { xs: "flex", sm: "none" } }}
                >
                  <CloseIcon />
                </IconButton>
              </Grid>
              <Grid size={{ xs: 11 }}>
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
          <Grid size={{ xs: 12, md: 9 }}>
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
        </Grid>
      </DialogTitle>
      <DialogContent dividers>
        {renderStep(
          steps[activeStep].name,
          selectedModelId,
          preselectedModelId,
          setSelectedModelId,
          setSelectedDatasetId,
          setNextEnabled,
          handlePredictNameInput,
          setTrainDataset,
          trainDataset,
          predictName,
          defaultName,
          setManualInputData,
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
  existingPredictions: PropTypes.array,
};

export default PredictionModal;
