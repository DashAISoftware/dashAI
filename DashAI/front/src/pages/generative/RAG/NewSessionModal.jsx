import React, { useState, useEffect, useCallback } from "react";
import {
  Button,
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

import DocumentSelectionStep from "./DocumentSelectionStep";
import ChunkingConfigurationStep from "./ChunkingConfigurationStep";
import RetrieverConfigurationStep from "./RetrieverConfigurationStep";
import GeneratorConfigurationStep from "./GeneratorConfigurationStep";

const steps = [
  {
    name: "select-documents",
    label: "Select documents",
    component: DocumentSelectionStep,
  },
  {
    name: "configure-chunking",
    label: "Configure chunking",
    component: ChunkingConfigurationStep,
  },
  {
    name: "configure-retriever",
    label: "Configure retriever",
    component: RetrieverConfigurationStep,
  },
  {
    name: "configure-generator",
    label: "Configure Language Model",
    component: GeneratorConfigurationStep,
  },
];

const defaultNewSession = {
  name: "",
  task_name: "RAGTask",
  description: "",
  displayName: "",
  parameters: {
    "documents": [],
    "chunking": {
       "parameters": {},
     },
    "retriever_model": {
      "name": "",
      "parameters": {},
    },
    "generator_model": { 
      "name": "",
      "parameters": {},
    },
  },
};

export default function NewSessionModal({
  open,
  onClose,
  onSessionSaved,
  onSessionSelect,
  session
}) {
  const theme = useTheme();
  const screenSm = useMediaQuery(theme.breakpoints.down("sm"));
  
  const [activeStep, setActiveStep] = useState(0);
  const [stepValidity, setStepValidity] = useState(new Array(steps.length).fill(false));
  const [sessionData, setSessionData] = useState(session || defaultNewSession);


  useEffect(() => {
    if (open) {
      setActiveStep(0);
      if(session) {
        const sessionParameters = session.parameters || {};
        const sessionDocuments = sessionParameters.documents || [];
        const sessionRetrieverModel = sessionParameters.retriever_model || {};
        const sessionGeneratorModel = sessionParameters.generator_model || {};
        setSessionData({
          id: session.id,
          name: session.name || "",
          task_name: session.task_name || "RAGTask",
          description: session.description || "",
          displayName: session.displayName || "",
          parameters: {
            documents: [...sessionDocuments],
            retriever_model: {
              ...sessionRetrieverModel, 
            },
            generator_model: {
              ...sessionGeneratorModel,
            },
          },
        })
      } else {
        setSessionData(defaultNewSession); 
      }
      setStepValidity(new Array(steps.length).fill(false));
    }
  }, [open, session]);

  const handleStepValidation = useCallback((stepIndex, isValid) => {
    setStepValidity(prev => {
      const newValidity = [...prev];
      newValidity[stepIndex] = isValid;
      return newValidity;
    });
  }, [])

  const isNextOrFinishEnabled = () => {
    if (!stepValidity[activeStep]) {
      return false;
    }
    if (activeStep === steps.length - 1) {
      return stepValidity.every(isValid => isValid);
    }
    return true;
  };

  const handleFinish = async () => {
    if (!stepValidity.every(isValid => isValid)) {
      return;
    }

    try {
      const finalSessionData = {
      ...sessionData,
      name: sessionData.name.trim(),
      description: sessionData.description.trim() || "",
      task_name: "RAGTask",
      parameters: {
        ...sessionData.parameters,
        documents: sessionData.parameters.documents || [],
        retriever_model: sessionData.parameters.retriever_model || {
          name: "",
          parameters: {},
        },
        generator_model: sessionData.parameters.generator_model || {
          name: "",
          parameters: {},
        },
      },
    };

      console.log("NewSessionModal: Final session data to save:", finalSessionData);

      const savedSession = await onSessionSaved(finalSessionData);


      if (onSessionSelect) {
        onSessionSelect(savedSession.id);
      }
      onClose();
    } catch (error) {
      console.error("NewSessionModal: Error saving session:", error);
    }
  };

  return (
    <Dialog
      open={open}
      fullScreen={screenSm}
      fullWidth
      maxWidth="lg"
      onClose={onClose}
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
                  onClick={onClose}
                  sx={{ display: { xs: "flex", sm: "none" } }}
                >
                  <CloseIcon />
                </IconButton>
              </Grid>
              <Grid item xs>
                <Typography variant="h6" component="h3" align="left">
                  {session ? "Edit" : "Create New"} RAG Session
                </Typography>
              </Grid>
            </Grid>
          </Grid>
          <Grid item xs={12} md={9}>
            <Stepper nonLinear activeStep={activeStep} sx={{ maxWidth: "100%" }}>
              {steps.map((step, index) => (
                <Step
                  key={step.name}
                  completed={stepValidity[index] && activeStep > index}
                  disabled={activeStep < index}>
                  <StepButton color="inherit" onClick={() => setActiveStep(index)}>
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
            
            documents={sessionData.parameters.documents}
            setDocuments={
              (docs) => setSessionData(prev => ({
                ...prev,
                parameters: { ...prev.parameters, documents: docs }
              }))
            }
            setNextEnabled={(isValid) => handleStepValidation(0, isValid)}
            sessionName={sessionData.name}
            setSesssionName={(name) => setSessionData(prev => ({
              ...prev,
              name: name
            }))}
            sessionDescription={sessionData.description}
            setSessionDescription={(description) => setSessionData(prev => ({
              ...prev,
              description: description
            }))}
          />
        )}
        {activeStep === 1 && (
          <ChunkingConfigurationStep
            chunkingModel={sessionData.parameters.chunking}
            setChunkingModel={(model) => setSessionData(prev => ({
              ...prev,
              parameters: { ...prev.parameters, chunking: model }
            }))}
            setNextEnabled={(isValid) => handleStepValidation(1, isValid)}
          />
        )}

        {activeStep === 2 && (
          <RetrieverConfigurationStep
            retrieverModel={sessionData.parameters.retriever_model}
            setRetrieverModel={(model) => setSessionData(prev => ({
              ...prev,
              parameters: { ...prev.parameters, retriever_model: model }
            }))}
            setNextEnabled={(isValid) => handleStepValidation(1, isValid)}
          />
        )}
        {activeStep === 3 && (
          <GeneratorConfigurationStep
            generatorModel={sessionData.parameters.generator_model}
            setGeneratorModel={(model) => setSessionData(prev => ({
              ...prev,
              parameters: { ...prev.parameters, generator_model: model }
            }))}
            setNextEnabled={(isValid) => handleStepValidation(2, isValid)}
          />
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={() => {
          activeStep === 0 ? onClose() : setActiveStep(prev => prev - 1);
        }}>
          {activeStep === 0 ? "Cancel" : "Back"}
        </Button>
        <Button
          variant="contained"
          onClick={() => activeStep === steps.length - 1 ? handleFinish() : setActiveStep(prev => prev + 1)}
          disabled={!isNextOrFinishEnabled()}
        >
          {activeStep === steps.length - 1 ? "Finish" : "Next"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}