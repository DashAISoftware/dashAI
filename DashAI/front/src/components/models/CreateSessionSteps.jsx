import { useState, useMemo, useEffect } from "react";
import PropTypes from "prop-types";
import { Box, Stepper, Step, StepLabel } from "@mui/material";
import { useSnackbar } from "notistack";
import { useFormik } from "formik";
import SetNameAndDatasetStep from "./SetNameAndDatasetStep";
import PrepareDatasetStep from "../experiments/PrepareDatasetStep";
import FormSchemaButtonGroup from "../shared/FormSchemaButtonGroup";
import JobQueueWidget from "../jobs/JobQueueWidget";
import { createExperiment } from "../../api/experiment";
import { generateSequentialName } from "../../utils/nameGenerator";

function CreateSessionSteps({
  backHome,
  selectedTask,
  datasets,
  handleSessionCreated,
  existingSessions = [],
  preselectedDatasetId = null,
}) {
  const [activeStep, setActiveStep] = useState(0);
  const { enqueueSnackbar } = useSnackbar();

  // Step 1 state: Name and Dataset
  const [selectedDataset, setSelectedDataset] = useState(
    preselectedDatasetId
      ? datasets.find((d) => d.id === preselectedDatasetId) || null
      : null,
  );

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

  const [nextEnabled, setNextEnabled] = useState(false);

  const steps = ["Select Dataset", "Prepare Dataset"];

  const { defaultName } = useMemo(() => {
    if (!selectedTask) {
      return { defaultName: "" };
    }

    const taskDisplayName =
      selectedTask.metadata?.display_name ||
      selectedTask.name
        .replace("Task", "")
        .replace(/([A-Z])/g, " $1")
        .trim();

    return generateSequentialName({
      base: `Session_${taskDisplayName}`,
      items: existingSessions,
      filter: (session) => session.task_name === selectedTask.name,
    });
  }, [selectedTask, existingSessions]);

  const formik = useFormik({
    initialValues: {
      name: "",
    },
    enableReinitialize: true,
    onSubmit: async (values) => {
      if (activeStep === 0) {
        // Moving to step 2
        setNewExp({
          name: values.name.trim(),
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
        // Create session
        await createSession();
      }
    },
  });

  useEffect(() => {
    if (selectedTask && defaultName && !formik.values.name.trim()) {
      formik.setFieldValue("name", defaultName);
    }
  }, [selectedTask, defaultName, formik]);

  // Calculate if next button should be enabled based on current step
  const isNextEnabled = (() => {
    if (activeStep === 0) {
      const isNameValid = formik.values.name.trim().length >= 4;
      const isDatasetValid = selectedDataset !== null;
      return isNameValid && isDatasetValid;
    }
    return nextEnabled;
  })();

  const getNameError = () => {
    if (!selectedDataset) {
      return null;
    }

    const currentName = formik.values.name.trim();
    if (!currentName) {
      return "Name is required";
    }

    const nameExists = existingSessions.some(
      (session) =>
        session.name &&
        session.name.toLowerCase() === currentName.toLowerCase(),
    );
    if (nameExists) {
      return "A session with this name already exists";
    }

    return null;
  };

  const nameError = getNameError();

  const handleBack = () => {
    if (activeStep === 0) {
      backHome();
    } else {
      setActiveStep(activeStep - 1);
    }
  };

  const createSession = async () => {
    try {
      setNextEnabled(false);
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
    <>
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
              formik={formik}
              selectedDataset={selectedDataset}
              setSelectedDataset={setSelectedDataset}
              datasets={datasets}
              nameError={nameError}
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
        <Box sx={{ display: "flex", justifyContent: "flex-end", p: 2 }}>
          <FormSchemaButtonGroup
            onCancel={handleBack}
            onFormSubmit={formik.handleSubmit}
            formik={{
              errors: {
                ...(nameError ? { name: nameError } : {}),
                ...(selectedDataset || activeStep === 1
                  ? {}
                  : { dataset: "Dataset is required" }),
                ...(!isNextEnabled && activeStep === 1
                  ? { validation: "Complete required fields" }
                  : {}),
              },
            }}
            saveButtonText={
              activeStep === steps.length - 1 ? "Create Session" : "Next"
            }
            backButtonText="Back"
          />
        </Box>
      </Box>

      {/* Job Queue Widget */}
      <Box
        sx={{
          position: "fixed",
          bottom: "20px",
          right: "20px",
          zIndex: 1000,
        }}
      >
        <JobQueueWidget />
      </Box>
    </>
  );
}
CreateSessionSteps.propTypes = {
  backHome: PropTypes.func.isRequired,
  selectedTask: PropTypes.object.isRequired,
  datasets: PropTypes.array.isRequired,
  handleSessionCreated: PropTypes.func,
  existingSessions: PropTypes.array,
  preselectedDatasetId: PropTypes.number,
};

export default CreateSessionSteps;
