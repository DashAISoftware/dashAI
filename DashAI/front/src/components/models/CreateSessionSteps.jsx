import { useState } from "react";
import PropTypes from "prop-types";
import { Box, Button, Stepper, Step, StepLabel } from "@mui/material";
import { useSnackbar } from "notistack";
import SetNameAndDatasetStep from "./SetNameAndDatasetStep";
import PrepareDatasetStep from "../experiments/PrepareDatasetStep";
import { createExperiment } from "../../api/experiment";

function CreateSessionSteps({
  backHome,
  selectedTask,
  datasets,
  handleSessionCreated,
  existingSessions = [],
}) {
  const [activeStep, setActiveStep] = useState(0);
  const [nextEnabled, setNextEnabled] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  // Step 1 state: Name and Dataset
  const [sessionName, setSessionName] = useState("");
  const [selectedDataset, setSelectedDataset] = useState(null);

  // Step 2 state: Prepare Dataset
  const [newExp, setNewExp] = useState({
    name: "",
    dataset: null,
    task_name: selectedTask?.name || "",
    input_columns: [],
    output_columns: [],
    splits: {},
    runs: [],
  });

  const steps = ["Select Dataset", "Prepare Dataset"];

  const handleNext = async () => {
    if (activeStep === 0) {
      // Moving from step 0 to step 1
      setNewExp({
        name: sessionName,
        dataset: selectedDataset,
        task_name: selectedTask?.name || "",
        input_columns: [],
        output_columns: [],
        splits: {},
        runs: [],
      });
      setActiveStep(1);
      setNextEnabled(false);
    } else if (activeStep === 1) {
      // Create session (experiment)
      await createSession();
    }
  };

  const handleBack = () => {
    if (activeStep === 0) {
      backHome();
    } else {
      setActiveStep(activeStep - 1);
      setNextEnabled(true);
    }
  };

  const createSession = async () => {
    try {
      const response = await createExperiment(
        newExp.dataset.id,
        newExp.task_name,
        newExp.name,
        newExp.input_columns,
        newExp.output_columns,
        JSON.stringify(newExp.splits),
      );

      enqueueSnackbar("Session successfully created.", {
        variant: "success",
      });

      // Call parent handler with created session
      if (handleSessionCreated) {
        handleSessionCreated(response);
      }

      // Reset and go back home
      backHome();
    } catch (error) {
      enqueueSnackbar("Error while trying to create session", {
        variant: "error",
      });
      console.error("Error creating session:", error);
    }
  };

  return (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Stepper */}
      <Box sx={{ p: 2 }}>
        <Stepper activeStep={activeStep}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Box>

      {/* Step content */}
      <Box sx={{ flexGrow: 1, overflow: "auto", p: 2 }}>
        {activeStep === 0 && (
          <SetNameAndDatasetStep
            sessionName={sessionName}
            setSessionName={setSessionName}
            selectedDataset={selectedDataset}
            setSelectedDataset={setSelectedDataset}
            datasets={datasets}
            setNextEnabled={setNextEnabled}
            existingSessions={existingSessions}
            selectedTask={selectedTask}
          />
        )}
        {activeStep === 1 && (
          <PrepareDatasetStep
            newExp={newExp}
            setNewExp={setNewExp}
            setNextEnabled={setNextEnabled}
          />
        )}
      </Box>

      {/* Footer with navigation buttons */}
      <Box
        sx={{
          p: 2,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <Button onClick={handleBack} variant="outlined">
          Back
        </Button>
        <Button
          onClick={handleNext}
          variant="contained"
          disabled={!nextEnabled}
        >
          {activeStep === steps.length - 1 ? "Create Session" : "Next"}
        </Button>
      </Box>
    </Box>
  );
}

CreateSessionSteps.propTypes = {
  backHome: PropTypes.func.isRequired,
  selectedTask: PropTypes.object.isRequired,
  datasets: PropTypes.array.isRequired,
  handleSessionCreated: PropTypes.func,
  existingSessions: PropTypes.array,
};

export default CreateSessionSteps;
