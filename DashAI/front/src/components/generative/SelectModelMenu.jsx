import { useEffect, useState, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Typography } from "@mui/material";
import { useFormik } from "formik";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { useTourContext } from "../tour/TourProvider";
import {
  getRelatedComponents,
  createGenerativeSession,
} from "../../api/generativeTask";
import {
  preprocessSchema,
  buildYupSchema,
  formatTaskNameForSession,
} from "./utils";
import { generateSequentialName } from "../../utils/nameGenerator";
import { useGenerative } from "./GenerativeContext";
import FormSchemaButtonGroup from "../shared/FormSchemaButtonGroup";
import ModelGrid from "./ModelGrid";
import SessionForm from "./SessionForm";

export default function SelectModelMenu() {
  const navigate = useNavigate();
  const {
    selectedTaskName,
    selectedDisplayName,
    sessions: existingSessions,
    setSessions,
  } = useGenerative();

  const [relatedComponents, setRelatedComponents] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [validationSchema, setValidationSchema] = useState(null);
  const [page, setPage] = useState(1);
  const [nameError, setNameError] = useState(false);
  const [nameErrorMessage, setNameErrorMessage] = useState("");

  const { t } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const tourContext = useTourContext();
  const hasAdvancedTourRef = useRef(false);

  const { defaultName } = useMemo(() => {
    if (!selectedTaskName) return { defaultName: "" };
    return generateSequentialName({
      base: `${formatTaskNameForSession(selectedTaskName)}_Session`,
      items: existingSessions,
      getName: (session) => session.name,
      filter: (session) => session.task_name === selectedTaskName,
    });
  }, [selectedTaskName, existingSessions]);

  useEffect(() => {
    if (!selectedTaskName) return;
    getRelatedComponents(selectedTaskName).then((components) => {
      setRelatedComponents(components);
      setPage(1);
      setSelectedModel((prev) =>
        prev ? (components.find((c) => c.name === prev.name) ?? prev) : null,
      );
    });
  }, [selectedTaskName, t]);

  useEffect(() => {
    if (!selectedModel?.schema?.properties) return;
    const processedProps = preprocessSchema(selectedModel.schema.properties);
    setValidationSchema(buildYupSchema(processedProps));
    const initialValues = Object.keys(processedProps).reduce(
      (acc, key) => {
        acc[key] = processedProps[key].placeholder || "";
        return acc;
      },
      { name: defaultName || "", description: "" },
    );
    formik.setValues(initialValues);
  }, [selectedModel, defaultName]);

  const formik = useFormik({
    initialValues: { name: "", description: "" },
    validationSchema,
    enableReinitialize: true,
    onSubmit: async (values) => {
      if (!values.name || values.name.trim() === "") {
        setNameError(true);
        setNameErrorMessage(t("generative:error.nameRequired"));
        return;
      }
      try {
        const createdSession = await createGenerativeSession({
          name: values.name,
          description: values.description,
          task_name: selectedTaskName,
          model_name: selectedModel?.name || "",
          parameters: values,
        });
        setSessions((prev) => [...prev, createdSession]);
        navigate(`/app/generative/sessions/${createdSession.id}`);
        enqueueSnackbar(t("generative:message.sessionCreatedSuccess"), {
          variant: "success",
        });
        if (tourContext?.run && tourContext?.stepIndex === 5) {
          const waitForElement = () => {
            const el = document.querySelector(
              '[data-tour="sessions-left-panel"]',
            );
            if (el) setTimeout(() => tourContext.nextStep(), 100);
            else setTimeout(waitForElement, 100);
          };
          setTimeout(waitForElement, 100);
        }
      } catch (error) {
        console.error("Error creating session:", error);
        const errorDetail = error?.response?.data?.detail || "";
        if (
          error?.response?.status === 409 ||
          errorDetail.includes("already exists")
        ) {
          enqueueSnackbar(t("generative:error.sessionNameExists"), {
            variant: "error",
          });
        } else {
          enqueueSnackbar(t("generative:error.failedToCreateSession"), {
            variant: "error",
          });
        }
      }
    },
  });

  const handleNameInputChange = (event) => {
    formik.handleChange(event);
    const empty = event.target.value.trim() === "";
    setNameError(empty);
    setNameErrorMessage(empty ? t("generative:error.nameRequired") : "");
  };

  const handleModelSelect = (model) => {
    setSelectedModel(model);
    if (
      tourContext?.run &&
      tourContext?.stepIndex === 3 &&
      !hasAdvancedTourRef.current
    ) {
      hasAdvancedTourRef.current = true;
      const waitForElement = () => {
        const el = document.querySelector('[data-tour="model-parameters"]');
        if (el) {
          const distanceToViewportCenter = Math.abs(
            el.getBoundingClientRect().top - window.innerHeight / 2,
          );
          const scrollWaitMs = Math.min(
            800,
            Math.max(300, Math.round(distanceToViewportCenter * 0.7)),
          );

          el.scrollIntoView({ behavior: "smooth", block: "center" });
          setTimeout(() => tourContext.nextStep(), scrollWaitMs);
          return;
        }

        setTimeout(waitForElement, 100);
      };
      setTimeout(waitForElement, 200);
    }
  };

  const processedProperties = selectedModel?.schema?.properties
    ? preprocessSchema(selectedModel.schema.properties)
    : {};

  return (
    <Box
      display="flex"
      height="100%"
      width="100%"
      flexDirection="column"
      justifyContent="flex-start"
      overflow="auto"
      pl={5}
      pr={5}
    >
      <Typography
        variant="h5"
        component="h2"
        sx={{ whiteSpace: "normal", wordBreak: "break-word", mt: 2, mb: 2 }}
      >
        {selectedDisplayName}:{" "}
        {t("generative:label.selectModelAndConfigureParameters")}
      </Typography>

      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
        {t("generative:label.selectModel")}
      </Typography>

      <ModelGrid
        models={relatedComponents}
        selectedModelName={selectedModel?.name}
        page={page}
        onSelect={handleModelSelect}
        onPageChange={setPage}
      />

      <Box sx={{ mb: 2 }} />

      {!selectedModel && (
        <Box sx={{ mt: 1 }}>
          <FormSchemaButtonGroup
            onCancel={() => navigate("/app/generative")}
            onFormSubmit={() => {}}
            error={true}
            saveButtonText={t("generative:button.createSession")}
            backButtonText={t("generative:button.backToTaskSelection")}
            justifyContent="flex-start"
          />
        </Box>
      )}

      {selectedModel?.schema && (
        <SessionForm
          formik={formik}
          processedProperties={processedProperties}
          nameError={nameError}
          nameErrorMessage={nameErrorMessage}
          onNameChange={handleNameInputChange}
          onBack={() => navigate("/app/generative")}
        />
      )}
    </Box>
  );
}
