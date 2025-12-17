import { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  Box,
  Typography,
  IconButton,
  Chip,
  Stepper,
  Step,
  StepLabel,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import { useFormik } from "formik";
import { useSnackbar } from "notistack";
import FormSchemaButtonGroup from "../shared/FormSchemaButtonGroup";
import { generateSequentialName } from "../../utils/nameGenerator";
import { formatDate } from "../../pages/results/constants/formatDate";
import PrepareDatasetStep from "../experiments/PrepareDatasetStep";
import { createExperiment } from "../../api/experiment";
import ItemSelectorWithInfo from "../custom/ItemSelectorWithInfo";

export function CreateSessionModal({
  open,
  onClose,
  onSessionCreated,
  dataset,
  datasetInfo,
  existingSessions = [],
  tasks = [],
}) {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedTask, setSelectedTask] = useState({});
  const [nextEnabled, setNextEnabled] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const [newSession, setNewSession] = useState({
    name: "",
    dataset: dataset,
    task_name: "",
    input_columns: [],
    output_columns: [],
    splits: {},
  });

  const steps = ["Select Task", "Name Session", "Prepare Dataset"];

  const { defaultName } = useMemo(() => {
    if (!selectedTask || !selectedTask.name) {
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
    onSubmit: async () => {
      if (activeStep === 0) {
        // Move to name step
        setActiveStep(1);
      } else if (activeStep === 1) {
        // Move to prepare dataset step
        setNewSession((prev) => ({
          ...prev,
          name: formik.values.name.trim(),
          task_name: selectedTask.name,
        }));
        setActiveStep(2);
        setNextEnabled(false);
      } else if (activeStep === 2) {
        // Create session
        await createSession();
      }
    },
  });

  useEffect(() => {
    if (open) {
      // Reset state when modal opens
      setActiveStep(0);
      setSelectedTask({});
      setNextEnabled(false);
      formik.resetForm();
      setNewSession({
        name: "",
        dataset: dataset,
        task_name: "",
        input_columns: [],
        output_columns: [],
        splits: {},
      });
    }
  }, [open, dataset]);

  useEffect(() => {
    if (selectedTask && defaultName && !formik.values.name.trim()) {
      formik.setFieldValue("name", defaultName);
    }
  }, [selectedTask, defaultName]);

  const getNameError = () => {
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

  const isNextEnabled = (() => {
    if (activeStep === 0) {
      return selectedTask && Object.keys(selectedTask).length > 0;
    } else if (activeStep === 1) {
      return formik.values.name.trim().length >= 4 && !nameError;
    } else if (activeStep === 2) {
      return nextEnabled;
    }
    return false;
  })();

  const handleBack = () => {
    if (activeStep === 0) {
      handleClose();
    } else {
      setActiveStep(activeStep - 1);
    }
  };

  const createSession = async () => {
    try {
      const response = await createExperiment(
        newSession.dataset.id,
        newSession.task_name,
        newSession.name,
        newSession.input_columns,
        newSession.output_columns,
        JSON.stringify(newSession.splits),
      );

      enqueueSnackbar("Session successfully created.", {
        variant: "success",
      });

      if (onSessionCreated) {
        onSessionCreated(response);
      }

      handleClose();
    } catch (error) {
      enqueueSnackbar("Error while trying to create session", {
        variant: "error",
      });
      console.error("Error creating session:", error);
    }
  };

  const handleClose = () => {
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Create a New Session
        <IconButton
          onClick={handleClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {/* Stepper */}
          <Stepper activeStep={activeStep} sx={{ mb: 2 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {/* Selected Dataset Info */}
          {dataset && (
            <Box
              sx={{
                p: 2,
                border: 1,
                borderColor: "divider",
                borderRadius: 2,
                mb: 2,
              }}
            >
              <Typography variant="h6" gutterBottom>
                Selected Dataset
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="body2" fontWeight="medium">
                    Name:
                  </Typography>
                  <Chip label={dataset.name} size="small" />
                </Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="body2" fontWeight="medium">
                    Created:
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(dataset.created)}
                  </Typography>
                </Box>
                <Typography variant="body2" fontWeight="medium">
                  Rows: {datasetInfo?.total_rows ?? "-"} | Columns:{" "}
                  {datasetInfo?.total_columns ?? "-"}
                </Typography>
              </Box>
            </Box>
          )}

          {/* Step Content */}
          <Box sx={{ minHeight: 300 }}>
            {activeStep === 0 && (
              <ItemSelectorWithInfo
                itemsList={tasks}
                selectedItem={selectedTask}
                setSelectedItem={setSelectedTask}
              />
            )}

            {activeStep === 1 && (
              <Box>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Name your Session
                </Typography>
                <TextField
                  fullWidth
                  label="Session Name"
                  name="name"
                  value={formik.values.name}
                  onChange={formik.handleChange}
                  variant="outlined"
                  error={Boolean(nameError)}
                  helperText={nameError}
                  slotProps={{
                    inputLabel: { shrink: true },
                  }}
                />
                {selectedTask && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      Task:{" "}
                      {selectedTask.metadata?.display_name || selectedTask.name}
                    </Typography>
                  </Box>
                )}
              </Box>
            )}

            {activeStep === 2 && (
              <PrepareDatasetStep
                newExp={newSession}
                setNewExp={setNewSession}
                setNextEnabled={setNextEnabled}
              />
            )}
          </Box>

          {/* Navigation Buttons */}
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
            <FormSchemaButtonGroup
              onCancel={handleBack}
              onFormSubmit={formik.handleSubmit}
              formik={{ errors: nameError ? { name: nameError } : {} }}
              saveButtonText={
                activeStep === steps.length - 1 ? "Create Session" : "Next"
              }
              backButtonText={activeStep === 0 ? "Cancel" : "Back"}
              disabled={!isNextEnabled}
            />
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
