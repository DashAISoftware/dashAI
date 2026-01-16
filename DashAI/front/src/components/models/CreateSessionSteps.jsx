import { useState, useMemo, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { Box, Stepper, Step, StepLabel } from "@mui/material";
import { useSnackbar } from "notistack";
import { useFormik } from "formik";
import { useTourContext } from "../tour/TourProvider";
import SetNameAndDatasetStep from "./SetNameAndDatasetStep";
import PrepareDatasetStep from "../experiments/PrepareDatasetStep";
import FormSchemaButtonGroup from "../shared/FormSchemaButtonGroup";
import JobQueueWidget from "../jobs/JobQueueWidget";
import { createExperiment } from "../../api/experiment";
import { getComponents } from "../../api/component";
import { generateSequentialName } from "../../utils/nameGenerator";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation(["models", "common"]);
  const tourContext = useTourContext();
  const hasAdvancedTourRef = useRef(false);

  const [selectedDataset, setSelectedDataset] = useState(
    preselectedDatasetId
      ? datasets.find((d) => d.id === preselectedDatasetId) || null
      : null,
  );

  const handleDatasetChange = (newDataset) => {
    setSelectedDataset(newDataset);
    if (
      tourContext?.run &&
      tourContext?.stepIndex === 5 &&
      newDataset &&
      !hasAdvancedTourRef.current
    ) {
      hasAdvancedTourRef.current = true;
      const waitForElement = () => {
        const element = document.querySelector(
          '[data-tour="models-next-button"]',
        );
        if (element) {
          setTimeout(() => {
            tourContext.nextStep();
          }, 100);
        } else {
          setTimeout(waitForElement, 100);
        }
      };
      setTimeout(waitForElement, 200);
    }
  };

  const [newExp, setNewExp] = useState({
    name: "",
    dataset: null,
    task_name: selectedTask?.name || "",
    input_columns: [],
    output_columns: [],
    train_metrics: [],
    validation_metrics: [],
    test_metrics: [],
    splits: {},
    runs: [],
  });

  const [nextEnabled, setNextEnabled] = useState(false);

  const steps = [
    t("models:label.selectDataset"),
    t("models:label.prepareDataset"),
  ];

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
        setNewExp((prev) => ({
          ...prev,
          name: values.name.trim(),
          dataset: selectedDataset,
          task_name: selectedTask?.name || "",
        }));
        setActiveStep(1);
        setNextEnabled(false);

        if (tourContext?.run && tourContext?.stepIndex === 6) {
          const waitForElement = () => {
            const element = document.querySelector(
              '[data-tour="models-validation-alert"]',
            );
            if (element) {
              setTimeout(() => {
                tourContext.nextStep();
              }, 100);
            } else {
              setTimeout(waitForElement, 100);
            }
          };
          setTimeout(waitForElement, 300);
        }
      } else if (activeStep === 1) {
        await createSession();
      }
    },
  });

  useEffect(() => {
    if (selectedTask && defaultName && !formik.values.name.trim()) {
      formik.setFieldValue("name", defaultName);
    }
  }, [selectedTask, defaultName, formik]);

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
      return t("models:error.nameRequired");
    }

    const nameExists = existingSessions.some(
      (session) =>
        session.name &&
        session.name.toLowerCase() === currentName.toLowerCase(),
    );
    if (nameExists) {
      return t("models:error.sessionNameExists");
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

      let allMetricNames = [];
      try {
        const metricsData = await getComponents({
          selectTypes: ["Metric"],
          relatedComponent: newExp.task_name,
        });
        allMetricNames = metricsData.map((metric) => metric.name);
      } catch (error) {
        console.warn("Could not fetch metrics:", error);
      }

      const hasTrain =
        newExp.splits.train !== undefined && newExp.splits.train !== 0;
      const hasValidation =
        newExp.splits.validation !== undefined &&
        newExp.splits.validation !== 0;
      const hasTest =
        newExp.splits.test !== undefined && newExp.splits.test !== 0;

      const trainMetrics = hasTrain ? allMetricNames : [];
      const validationMetrics = hasValidation ? allMetricNames : [];
      const testMetrics = hasTest ? allMetricNames : [];

      const response = await createExperiment(
        newExp.dataset.id,
        newExp.task_name,
        newExp.name,
        newExp.input_columns,
        newExp.output_columns,
        trainMetrics,
        validationMetrics,
        testMetrics,
        JSON.stringify(newExp.splits),
      );

      enqueueSnackbar(t("models:message.sessionCreatedSuccess"), {
        variant: "success",
      });

      if (tourContext?.run) {
        tourContext.stopTour();
        sessionStorage.setItem("startModelsSessionTour", "true");
      }

      if (handleSessionCreated) {
        handleSessionCreated(response);
      }

      backHome();
    } catch (error) {
      enqueueSnackbar(t("models:error.createSession"), {
        variant: "error",
      });
      console.error("Error creating session:", error);
    }
  };

  return (
    <>
      <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <Box sx={{ p: 2 }}>
          <Stepper activeStep={activeStep}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        <Box sx={{ flexGrow: 1, overflow: "auto", p: 2 }}>
          {activeStep === 0 && (
            <SetNameAndDatasetStep
              formik={formik}
              selectedDataset={selectedDataset}
              setSelectedDataset={handleDatasetChange}
              datasets={datasets}
              nameError={nameError}
              selectedTask={selectedTask}
              onDatasetChange={handleDatasetChange}
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

        <Box sx={{ display: "flex", justifyContent: "flex-end", p: 2 }}>
          <FormSchemaButtonGroup
            onCancel={handleBack}
            onFormSubmit={formik.handleSubmit}
            dataTour="models-next-button"
            formik={{
              errors: {
                ...(nameError ? { name: nameError } : {}),
                ...(selectedDataset || activeStep === 1
                  ? {}
                  : { dataset: t("models:error.datasetRequired") }),
                ...(!isNextEnabled && activeStep === 1
                  ? { validation: t("models:error.completeRequiredFields") }
                  : {}),
              },
            }}
            saveButtonText={
              activeStep === steps.length - 1
                ? t("models:button.createSession")
                : t("common:next")
            }
            backButtonText={t("common:back")}
          />
        </Box>
      </Box>

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
