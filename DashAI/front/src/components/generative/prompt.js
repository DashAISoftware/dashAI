Ayudame a hacer que este código funcione, llamando correctamente a las APIs y manteniendo el estilo definido. Puedes modificar y refactorizar todo lo necesario, pero tienes prohibido cambiar la estética de los componentes y el código de NewSessionModal (el resto sí puedes modificarlo)

La idea es poder crear una sesión de rag del siguiente modo:

1. Se cargan (desde el back) y muestran todas las sesiones disponibles

2. Si se crea una nueva sesión, se abre un modal

3. Se seleccionan los documentos

4. Se configura el Retriever. Para ello:

4.1. Se cargan desde el back los retriever disponibles

4.2 El usuario selecciona un modelo

4.3 Se muetran los parámetros por defecto del modelo

4.4 Si el usuario desea puede modificar los parámetros

4.5 Al hacer click en Next se guardan (con un post al backend) los parámetros del Retriever de la sesión

5. Se configura el LLM

//imports

export default function Generative() {
  const [stepIndex, setStepIndex] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedTaskName, setSelectedTaskName] = useState("");
  const [sessions, setSessions] = useState([]);
  const [paramsVersion, setParamsVersion] = useState(0);

  const isRAGTask = () => selectedTaskName === "RAGTask";

  const handleSessionClick = (sessionId, taskName) => {
    console.log("[handleSessionClick]", { sessionId, taskName });
    setSelectedTaskName(taskName);
    setSelectedSessionId(sessionId);
  };

  const handleNewSessionButton = () => {
    console.log("[handleNewSessionButton]");
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
  };

  const onParamsUpdate = (newParams) => {
    console.log("[onParamsUpdate]", newParams);
    setParamsVersion((prev) => prev + 1);
  };

  useEffect(() => {
    getSessions().then((data) => {
      console.log("[getSessions]", data);
      setSessions(data);
    });
  }, []);

  const handleAddSession = (session) => {
    console.log("[handleAddSession]", session);
    setSessions((prevSessions) => [session, ...prevSessions]);
  };

  const handleSessionDelete = (id) => {
    console.log("[handleSessionDelete]", id);
    if (id === selectedSessionId) {
      setSelectedSessionId(null);
      setStepIndex(0);
      setSelectedTaskName("");
    }

    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id)
    );

    removeSession(id);
  };

  return (
    <Box height="calc(100vh - 74px)" width="100%" p={1.5} pb={1} display="flex">
      <Box width="22%" mr={1}>
        <SessionBar
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          handleSessionClick={handleSessionClick}
          handleNewSessionButton={handleNewSessionButton}
          handleSessionDelete={handleSessionDelete}
          stepIndex={stepIndex}
        />
      </Box>

      <Box width="56%" mr={1}>
        <MainGenerativeBox>
          {selectedSessionId ? (
            isRAGTask() ? (
              <GenerativeChat
                sessionId={selectedSessionId}
                taskName={selectedTaskName}
                paramsVersion={paramsVersion}
              />
              ) : (
              <GenerativeChat
                sessionId={selectedSessionId}
                taskName={selectedTaskName}
                paramsVersion={paramsVersion}
              />
              )
            ) : stepIndex === 0 ? (
              <SelectTaskMenu
                goToNextStep={(taskName) => {
                  console.log("[SelectTaskMenu] task selected:", taskName);
                  setSelectedTaskName(taskName);
                  setStepIndex(1);
                }}
              />
              ) : isRAGTask() ? (
                <RAGHomePage
                  handleAddSession={handleAddSession}
                  selectedTaskName={selectedTaskName}
                  setSelectedSessionId={setSelectedSessionId}
                />
              ) : (
                <SelectModelMenu
                  handleAddSession={handleAddSession}
                  selectedTaskName={selectedTaskName}
                  setSelectedSessionId={setSelectedSessionId}
                />
              )
          }
        </MainGenerativeBox>
      </Box>
      
      {!isRAGTask() && (
      <Box width="22%">
        <Box
          width="100%"
          height="100%"
          sx={{ backgroundColor: "background.box", borderRadius: 2 }}
        >
          {!selectedSessionId ?
            (
              <ParamsBar
                selectedSessionId={selectedSessionId}
                onParamsUpdate={onParamsUpdate}
                taskName={selectedTaskName}
              />
            ): null}
        </Box>
      </Box>
        )
        }
    </Box>
  );
}
//imports

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


// imports
function RAGHomePage({
    selectedTaskName,
    setSelectedSessionId,
    handleAddSession
    }) {
    
    ...

    return (
        <CustomLayout
            title="RAG Sessions"
            subtitle="Manage your RAG sessions"
        >
            {showNewSessionModal? (
                <NewSessionModal
                    open={showNewSessionModal}
                    setOpen={setShowNewSessionModal}
                    setUpdateTableFlag={setUpdateTableFlag}
                    setSelectedSessionId={setSelectedSessionId}
                    handleAddSession={handleAddSession}
                    selectedSession={selectedSession}
                />
            ):(
                <RAGSessionsTable
                    handleOpenNewSessionModal={handleOpenNewSessionModal}
                    onSessionSelect={handleSessionSelect}
                    updateTableFlag={updateTableFlag}
                    setUpdateTableFlag={setUpdateTableFlag}
                />
            )
            }
        </CustomLayout>
    );
}

export default RAGHomePage;

// imports

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

...
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

// imports
function RetrieverConfigurationStep({ newSession, setNewSession, setNextEnabled }) {
  const handleConfigurationChange = (retrieverConfig) => {
    setNewSession(prev => ({
      ...prev,
      RAGParameters: {
        ...prev.RAGParameters,
        retrieval: retrieverConfig
      }
    }));
  };
  console.log("Retriever initial values:", newSession.RAGParameters?.retrieval);
  console.log("New session state:", newSession);

  return (
    <Box sx={{ height: "100%", overflow: "auto" }}>
      <ComponentSelector
        componentType="Retriever"
        fetchComponents={getRetrieverComponents}
        initialValues={newSession.RAGParameters?.retrieval}
        onConfigurationChange={handleConfigurationChange}
        setNextEnabled={setNextEnabled}
      />
    </Box>
  );
}

RetrieverConfigurationStep.propTypes = {
  newSession: PropTypes.object.isRequired,
  setNewSession: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default RetrieverConfigurationStep;

// imports

import { getRelatedComponents } from "../../../api/generativeTask";
function ComponentSelector({
  componentType,
  fetchComponents,
  initialValues,
  onConfigurationChange,
  setNextEnabled
}) {
  const [components, setComponents] = useState([]);
  const [selectedComponent, setSelectedComponent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [validationSchema, setValidationSchema] = useState(null);

  // Fetch available components
  useEffect(() => {
    const getComponents = async () => {
      setLoading(true);
      try {
        const data = await fetchComponents();
        setComponents(data);
        
        // If we have initialValues with a model_name, select that component
        if (initialValues?.model_name) {
          const preselectedComponent = data.find(c => c.name === initialValues.model_name);
          if (preselectedComponent) {
            setSelectedComponent(preselectedComponent);
          }
        } else {
          console.warn(`No initial model_name provided for ${componentType} selection.`);
        }
      } catch (error) {
        console.error(`Error fetching ${componentType} components:`, error);
      } finally {
        setLoading(false);
      }
    };
    
    getComponents();
  }, [componentType, fetchComponents]);

  // Set up form validation schema when component changes
  useEffect(() => {
    if (selectedComponent?.schema?.properties) {
      const processedProps = preprocessSchema(selectedComponent.schema.properties);
      setValidationSchema(buildYupSchema(processedProps));
      console.log("Processed properties for form:", processedProps);
      // Merge any existing values with defaults from schema
      const schemaDefaults = Object.keys(processedProps).reduce(
        (acc, key) => {
          acc[key] = processedProps[key].placeholder || "";
          console.log(`Setting default for ${key}:`, acc[key]);
          return acc;
        }, 
        { name: "", description: ""});
      
      // Preserve any values that were already set
      const mergedValues = {
        ...schemaDefaults,
        ...(initialValues?.parameters || {})
      };
      
      formik.setValues(mergedValues);
    }
  }, [selectedComponent]);

  const formik = useFormik({
    initialValues: initialValues?.parameters || {},
    validationSchema,
    enableReinitialize: true,
    onSubmit: (values) => {
      onConfigurationChange({
        model_name: selectedComponent.name,
        parameters: values
      });
    }
  });

  // Enable/disable next button based on form validity and selection
  useEffect(() => {
    if (selectedComponent && formik.isValid) {
      setNextEnabled(true);
      
      // Auto-submit valid values as they change
      if (formik.dirty) {
        onConfigurationChange({
          model_name: selectedComponent.name,
          parameters: formik.values
        });
      }
    } else {
      setNextEnabled(false);
    }
  }, [selectedComponent, formik.values, formik.isValid, formik.dirty]);

  // Process schema properties for the form renderer
  const processedProperties = selectedComponent?.schema?.properties
    ? preprocessSchema(selectedComponent.schema.properties)
    : {};

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Select {componentType}
      </Typography>
      
      {loading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Autocomplete
            disablePortal
            options={components.map(c => c.name)}
            value={selectedComponent?.name || null}
            onChange={(_, newValue) => {
              const selected = components.find(c => c.name === newValue);
              setSelectedComponent(selected);
            }}
            renderInput={(params) => (
              <TextField {...params} label={`${componentType} Model`} />
            )}
            sx={{ mb: 4 }}
          />
          
          {selectedComponent && (
            <form onSubmit={formik.handleSubmit}>
              <Typography variant="subtitle1" gutterBottom>
                {selectedComponent.name} Configuration
              </Typography>
              
              <FormSchemaRenderFields
                modelSchema={processedProperties}
                formik={formik}
                autoSave={true}
                handleUpdateSchema={(updatedValues) => {
                  formik.setValues({...formik.values, ...updatedValues});
                }}
                onFormSubmit={formik.handleSubmit}
                setError={(error) => console.error(error)}
                errorsMessage={formik.errors}
              />
            </form>
          )}
        </>
      )}
    </Box>
  );
}

ComponentSelector.propTypes = {
  componentType: PropTypes.string.isRequired,
  fetchComponents: PropTypes.func.isRequired,
  initialValues: PropTypes.object,
  onConfigurationChange: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired
};

export default ComponentSelector;

//RAG api
import api from "./api";
import { ISession } from "../types/session";
import { IGenerativeTask } from "../types/generativeTask";


// Fetch all RAG sessions
export const getRAGSessions = async (): Promise<ISession[]> => {
  console.log("Fetching all RAG sessions");

  const response = await api.get<ISession[]>("/v1/generative-session/");
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG sessions: ${response.statusText}`);
  }

  console.log("RAG sessions fetched successfully:", response.data);
  return response.data;
}

export const getRAGSession = async (sessionId: number): Promise<ISession> => {
  console.log(`Fetching RAG session with ID: ${sessionId}`);

  const response = await api.get<ISession>(`/v1/generative-session/${sessionId}`);
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG session: ${response.statusText}`);
  }

  console.log("RAG session fetched successfully:", response.data);
  return response.data;
}

export const createRAGSession = async (sessionData: Omit<ISession, "id" | "created" | "last_modified">): Promise<ISession> => {
  console.log("Creating new RAG session with data:", sessionData);

  const response = await api.post<ISession>("/v1/generative-session/", sessionData);
  if (response.status !== 201) {
    throw new Error(`Failed to create RAG session: ${response.statusText}`);
  }

  console.log("RAG session created successfully:", response.data);
  return response.data;
}

export const updateGenerativeSessionParams = async (
  sessionId: number,
  newParams: Record<string, any>,
): Promise<ISession> => {
  console.log(`Updating parameters for RAG session ID: ${sessionId} with data:
  ${JSON.stringify(newParams)}`);

  const response = await api.put<ISession>(
    `/v1/generative-session/${sessionId}/parameters`,
    newParams,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to update RAG session parameters: ${response.statusText}`);
  }
  console.log("RAG session parameters updated successfully:", response.data);
  return response.data;
}

export const getRAGComponents = async (): Promise<IGenerativeTask[]> => {
  // Simulate fetching RAG components based on type
  
  const response = await api.get(
    `/v1/component/?related_component=RAGTask`
  );

  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG components: ${response.statusText}`);
  }
  
  return response.data; 
};

export const getRetrieverComponents = async (): Promise<IGenerativeTask[]> => {
  const response = await api.get(
    `/v1/component/?selectTypes=RetrieverModel`
  );

  if (response.status !== 200) {
    throw new Error(`Failed to fetch retriever components: ${response.statusText}`);
  }
  
  return response.data;

}

export const getGeneratorComponents = async (): Promise<IGenerativeTask[]> => {

  const response = await api.get(
    `/v1/component/?related_component=GenerativeModel`
  );

  if (response.status !== 200) {
    throw new Error(`Failed to fetch generator components: ${response.statusText}`);
  }

  return response.data;

}