import React, { useState, useEffect } from "react";
import {
  Button,
  ButtonGroup,
  Dialog,
  DialogActions,
  DialogTitle,
  Grid,
  IconButton,
  Step,
  StepButton,
  DialogContent,
  Stepper,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useSnackbar } from "notistack";

import DocumentSelectionStep from "./DocumentSelectionStep";
import RetrieverConfigurationStep from "./RetrieverConfigurationStep";
import AlgorithmConfigurationStep from "./AlgorithmConfigurationStep";
import { createRAGSession, updateRAGSession } from "../../../api/rag";

const steps = [
  {
    name: "select-documents",
    label: "Select documents",
    Component: DocumentSelectionStep,
  },
  {
    name: "configure-retriever",
    label: "Configure retriever",
    Component: RetrieverConfigurationStep,
  },
  {
    name: "configure-algorithm",
    label: "Configure algorithm",
    Component: AlgorithmConfigurationStep,
  },
];

const defaultNewSession = {
  name: "",
  task_name: "RAGTask", // Default task name
  description: "",
  RAGParameters: {},
  documents: [],
};

export default function NewSessionModal({
  open,
  setOpen,
  setUpdateTableFlag,
  setSelectedSessionId,
  handleAddSession,
  selectedSession,
}) {
  const theme = useTheme();
  const matches = useMediaQuery(theme.breakpoints.down("md"));
  const screenSm = useMediaQuery(theme.breakpoints.down("sm"));
  const { enqueueSnackbar } = useSnackbar();

  const [activeStep, setActiveStep] = useState(0);
  const [nextEnabled, setNextEnabled] = useState(false);
  const [newSession, setNewSession] = useState(
    selectedSession || defaultNewSession
  );

  const [stepCompleted, setStepCompleted] = useState([false, false, false]);
  
  const handleStepComplete = (stepIndex) => {
    const newCompleted = [...stepCompleted];
    newCompleted[stepIndex] = true;
    setStepCompleted(newCompleted);
  };

  // Initialize session data when modal opens or selectedSession changes
  useEffect(() => {
    if (open) {
      if (selectedSession) {
        // Edit mode - use existing session
        setNewSession({
          ...selectedSession,
          // Ensure documents array exists
          documents: selectedSession.documents || []
        });
      } else {
        // Create mode - use defaults
        setNewSession(defaultNewSession);
      }
      setActiveStep(0);
      setNextEnabled(false);
    }
  }, [open, selectedSession]);


  const uploadNewSession = async () => {
    try {
      // For new sessions, exclude ID
      const sessionData = selectedSession 
        ? newSession // Keep existing ID for updates
        : { ...newSession, id: undefined }; // Remove ID for new sessions
      
      const response = selectedSession
        ? await updateRAGSession(sessionData) // Implement update function if needed
        : await createRAGSession(sessionData);

      const sessionId = response.id;
      console.log("Session created/updated with ID:", sessionId);

      enqueueSnackbar(
        `Session ${selectedSession ? "updated" : "created"} successfully!`,
        { variant: "success" }
      );
      setUpdateTableFlag(true); // Trigger table update
    } catch (error) {
      console.error("Session creation error:", error);
      enqueueSnackbar(
        `Failed to ${selectedSession ? "update" : "create"} session: ${error.message}`,
        { variant: "error" }
      );
    }
  };

  const handleCloseDialog = () => {
    setActiveStep(0);
    setOpen(false);
    setNewSession(defaultNewSession);
    setNextEnabled(false);

  };

  const handleStepButton = (index) => () => {
    setActiveStep(index);
  };

  const handleBackButton = () => {
    if (activeStep === 0) {
      handleCloseDialog();
    } else {
      setActiveStep(activeStep - 1);
      setNextEnabled(true);
    }
  };

  const handleNextButton = () => {
    if (activeStep === steps.length - 1) {
      handleFinish();
    } else {
      setActiveStep(activeStep + 1);
      setNextEnabled(false); // Reset next enabled for new step
    }
  };

  const handleFinish = async () => {
    await uploadNewSession();
    handleCloseDialog();
  };

  return (
    <Dialog
      open={open}
      fullScreen={screenSm}
      fullWidth
      maxWidth="lg"
      onClose={handleCloseDialog}
      aria-labelledby="new-session-dialog-title"
      PaperProps={{ sx: { minHeight: "80vh" } }}
    >
      <DialogTitle id="rag-configuration-wizard-title">
        <Grid container direction="row" alignItems="center">
          <Grid item xs={12} md={3}>
            <Grid container alignItems="center" justifyContent="space-between">
              <Grid item>
                <IconButton
                  edge="start"
                  color="inherit"
                  onClick={handleCloseDialog}
                  sx={{ display: { xs: "flex", sm: "none" } }}
                >
                  <CloseIcon />
                </IconButton>
              </Grid>
              <Grid item xs>
                <Typography variant="h6" component="h3" align="left">
                  {selectedSession ? "Edit" : "Create New"} RAG Session
                </Typography>
              </Grid>
            </Grid>
          </Grid>
          <Grid item xs={12} md={9}>
            <Stepper nonLinear activeStep={activeStep} sx={{ maxWidth: "100%" }}>
              {steps.map((step, index) => (
                <Step 
                  key={step.name} 
                  completed={activeStep > index}
                  disabled={activeStep < index}>
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
        {activeStep === 0 && (
          <DocumentSelectionStep
            newSession={newSession}
            setNewSession={setNewSession}
            setNextEnabled={setNextEnabled}
          />
        )}
        {activeStep === 1 && (
          <RetrieverConfigurationStep
            newSession={newSession}
            setNewSession={setNewSession}
            setNextEnabled={setNextEnabled}
          />
        )}
        {activeStep === 2 && (
          <AlgorithmConfigurationStep
            newSession={newSession}
            setNewSession={setNewSession}
            setNextEnabled={setNextEnabled}
            setSelectedSessionId={setSelectedSessionId}
            handleAddSession={handleAddSession}
          />
        )}
      </DialogContent>

      <DialogActions>
        <ButtonGroup size="large">
          <Button onClick={handleBackButton}>
            {activeStep === 0 ? "Cancel" : "Back"}
          </Button>
          <Button
            onClick={handleNextButton}
            variant="contained"
            disabled={!nextEnabled}
          >
            {activeStep === steps.length - 1 ? "Finish" : "Next"}
          </Button>
        </ButtonGroup>
      </DialogActions>
    </Dialog>
  );
}
