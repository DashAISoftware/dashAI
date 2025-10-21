import React, { useState, useEffect, useCallback, useRef } from "react";
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
import PromptConfigurationStep from "./PromptConfigurationStep";
import { generateSequentialName } from "../../../../utils/nameGenerator";

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
  {
    name: "configure-prompt",
    label: "Configure Prompt",
    component: PromptConfigurationStep,
  },
];

const defaultNewSession = {
  name: "",
  task_name: "RAGTask",
  description: "",
  displayName: "",
  parameters: {
    documents: [],
    chunking_model: {
      component: "",
      params: {},
    },
    retriever_model: {
      component: "",
      params: {},
    },
    generator_model: {
      component: "",
      params: {},
    },
    prompt_model: {
      component: "CustomGenerationPrompt",
      params: {
        template:
          "Answer to this message: {input}, with the following information: {chunks}",
      },
    },
  },
};

export default function NewSessionModal({
  open,
  onClose,
  onSessionSaved,
  onSessionSelect,
  session,
  existingSessions = [],
}) {
  const theme = useTheme();
  const screenSm = useMediaQuery(theme.breakpoints.down("sm"));

  const [activeStep, setActiveStep] = useState(0);
  const [stepValidity, setStepValidity] = useState(
    new Array(steps.length).fill(false),
  );
  const [sessionData, setSessionData] = useState(session || defaultNewSession);
  const retrieverStepRef = useRef(null);

  useEffect(() => {
    if (open) {
      setActiveStep(0);
      if (session) {
        const sessionParameters = session.parameters || {};
        const sessionDocuments = sessionParameters.documents || [];
        const sessionChunkingModel = sessionParameters.chunking_model || {};
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
            chunking_model: {
              ...sessionChunkingModel,
            },
            retriever_model: {
              ...sessionRetrieverModel,
            },
            generator_model: {
              ...sessionGeneratorModel,
            },
          },
        });
      } else {
        const { defaultName } = generateSequentialName({
          base: "RAG_Session",
          items: existingSessions,
          getName: (session) => session.name,
          filter: (session) => session.task_name === "RAGTask",
        });

        setSessionData({
          ...defaultNewSession,
          name: defaultName || "",
        });
      }
      setStepValidity(new Array(steps.length).fill(false));
    }
  }, [open, session, existingSessions]);

  const handleStepValidation = useCallback((stepIndex, isValid) => {
    setStepValidity((prev) => {
      const newValidity = [...prev];
      newValidity[stepIndex] = isValid;
      return newValidity;
    });
  }, []);

  const updateSessionDocuments = useCallback((docs) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: { ...prev.parameters, documents: docs },
    }));
  }, []);

  const updateSessionName = useCallback((name) => {
    setSessionData((prev) => ({
      ...prev,
      name: name,
    }));
  }, []);

  const updateSessionDescription = useCallback((description) => {
    setSessionData((prev) => ({
      ...prev,
      description: description,
    }));
  }, []);

  const updateRetrieverModel = useCallback((model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: { ...prev.parameters, retriever_model: model },
    }));
  }, []);

  const updateChunkingModel = useCallback((model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: { ...prev.parameters, chunking_model: model },
    }));
  }, []);

  const updateGeneratorModel = useCallback((model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: { ...prev.parameters, generator_model: model },
    }));
  }, []);

  const isNextOrFinishEnabled = () => {
    if (!stepValidity[activeStep]) {
      return false;
    }
    if (activeStep === steps.length - 1) {
      return stepValidity.every((isValid) => isValid);
    }
    return true;
  };

  const handleFinish = async () => {
    if (!stepValidity.every((isValid) => isValid)) {
      return;
    }

    try {
      const finalSessionData = {
        ...sessionData,
        name: sessionData.name.trim(),
        description: sessionData.description.trim() || "",
        model_name: "RAGPipeline",
        task_name: "RAGTask",
        parameters: {
          documents: sessionData.parameters.documents || [],
          chunking_model: sessionData.parameters.chunking_model || {
            component: "",
            params: {},
          },
          retriever_model: sessionData.parameters.retriever_model || {
            component: "",
            params: {},
          },
          generation_model: sessionData.parameters.generator_model || {
            component: "",
            params: {},
          },
          prompt_model: sessionData.parameters.prompt_model || {
            component: "CustomGenerationPrompt",
            params: {
              template:
                "Answer to this message: {input}, with the following information: {chunks}",
            },
          },
        },
      };

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
            <Stepper
              nonLinear
              activeStep={activeStep}
              sx={{ maxWidth: "100%" }}
            >
              {steps.map((step, index) => (
                <Step
                  key={step.name}
                  completed={stepValidity[index] && activeStep > index}
                  disabled={activeStep < index}
                >
                  <StepButton
                    color="inherit"
                    onClick={() => setActiveStep(index)}
                  >
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
            setDocuments={updateSessionDocuments}
            setNextEnabled={(isValid) => handleStepValidation(0, isValid)}
            sessionName={sessionData.name}
            setSesssionName={updateSessionName}
            sessionDescription={sessionData.description}
            setSessionDescription={updateSessionDescription}
          />
        )}
        {activeStep === 2 && (
          <RetrieverConfigurationStep
            ref={retrieverStepRef}
            retrieverModel={sessionData.parameters.retriever_model}
            setRetrieverModel={updateRetrieverModel}
            setNextEnabled={(isValid) => handleStepValidation(2, isValid)}
          />
        )}
        {activeStep === 1 && (
          <ChunkingConfigurationStep
            chunkingModel={sessionData.parameters.chunking_model}
            setChunkingModel={updateChunkingModel}
            setNextEnabled={(isValid) => handleStepValidation(1, isValid)}
          />
        )}

        {activeStep === 3 && (
          <GeneratorConfigurationStep
            generatorModel={sessionData.parameters.generator_model}
            setGeneratorModel={updateGeneratorModel}
            setNextEnabled={(isValid) => handleStepValidation(3, isValid)}
          />
        )}
      </DialogContent>

      <DialogActions>
        <Button
          onClick={() => {
            activeStep === 0 ? onClose() : setActiveStep((prev) => prev - 1);
          }}
        >
          {activeStep === 0 ? "Cancel" : "Back"}
        </Button>
        <Button
          variant="contained"
          onClick={() => {
            if (activeStep === 2 && retrieverStepRef.current) {
              retrieverStepRef.current.saveFormValues();
            }

            if (activeStep === steps.length - 1) {
              handleFinish();
            } else {
              setActiveStep((prev) => prev + 1);
            }
          }}
          disabled={!isNextOrFinishEnabled()}
        >
          {activeStep === steps.length - 1 ? "Finish" : "Next"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
