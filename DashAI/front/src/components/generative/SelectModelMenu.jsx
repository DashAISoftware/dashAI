import { useEffect, useState, useMemo } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
} from "@mui/material";
import { useFormik } from "formik";
import { useSnackbar } from "notistack";
import FormSchemaRenderFields from "../../components/shared/FormSchemaRenderFields";
import { getRelatedComponents } from "../../api/generativeTask";
import { createGenerativeSession } from "../../api/generativeTask";
import { preprocessSchema, buildYupSchema } from "./utils";
import { generateSequentialName } from "../../utils/nameGenerator";
import { useTranslation } from "react-i18next";
import { useGenerative } from "../../components/generative/GenerativeContext";

// Helper function to convert TaskName to readable format
const formatTaskNameForSession = (taskName) => {
  if (!taskName) return "";
  const cleaned = taskName.replace(/Task$/, "").replace(/Generation$/, "");
  return cleaned;
};

export default function SelectModelMenu() {
  const {
    selectedTaskName,
    selectedDisplayName,
    setSelectedSessionId,
    sessions: existingSessions,
    setStepIndex,
    setSessions,
  } = useGenerative();

  const [relatedComponents, setRelatedComponents] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [validationSchema, setValidationSchema] = useState(null);

  const [nameError, setNameError] = useState(false);
  const [nameErrorMessage, setNameErrorMessage] = useState("");

  const { t } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();

  const goToBackStep = () => {
    setStepIndex(0);
  };

  // Generate default name based on task and existing sessions
  const { defaultName } = useMemo(() => {
    if (!selectedTaskName) {
      return { defaultName: "" };
    }

    const formattedTaskName = formatTaskNameForSession(selectedTaskName);

    return generateSequentialName({
      base: `${formattedTaskName}_Session`,
      items: existingSessions,
      getName: (session) => session.name,
      filter: (session) => session.task_name === selectedTaskName,
    });
  }, [selectedTaskName, existingSessions]);

  useEffect(() => {
    if (!selectedTaskName) return;

    getRelatedComponents(selectedTaskName).then(setRelatedComponents);
  }, [selectedTaskName]);

  useEffect(() => {
    if (selectedModel?.schema?.properties) {
      const processedProps = preprocessSchema(selectedModel.schema.properties);

      setValidationSchema(buildYupSchema(processedProps));
      const initialValues = Object.keys(processedProps).reduce(
        (acc, key) => {
          acc[key] = processedProps[key].placeholder || "";
          return acc;
        },
        {
          name: defaultName || "",
          description: "",
        },
      );

      formik.setValues(initialValues);
    }
  }, [selectedModel, defaultName]);

  const handleAddSession = (session) => {
    setSessions((prevSessions) => [...prevSessions, session]);
  };

  const handleNameInputChange = (event) => {
    formik.handleChange(event);

    if (event.target.value.trim() === "") {
      setNameError(true);
      setNameErrorMessage(t("generative:error.nameRequired"));
    } else {
      setNameError(false);
      setNameErrorMessage("");
    }
  };

  const formik = useFormik({
    initialValues: {
      name: "",
      description: "",
    },
    validationSchema,
    enableReinitialize: true,
    onSubmit: async (values) => {
      if (!values.name || values.name.trim() === "") {
        setNameError(true);
        setNameErrorMessage(t("generative:error.nameRequired"));
        return;
      }

      try {
        const sessionData = {
          name: values.name,
          description: values.description,
          task_name: selectedTaskName,
          model_name: selectedModel?.name || "",
          parameters: values,
        };

        const createdSession = await createGenerativeSession(sessionData);

        setSelectedSessionId(createdSession.id);
        handleAddSession(createdSession);

        enqueueSnackbar(t("generative:message.sessionCreatedSuccess"), {
          variant: "success",
        });
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

  const processedProperties = selectedModel?.schema?.properties
    ? preprocessSchema(selectedModel.schema.properties)
    : {};

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
      pl={5}
      pr={5}
    >
      <Typography
        variant="h5"
        component="h2"
        sx={{
          whiteSpace: "normal",
          wordBreak: "break-word",
          mt: 2,
          mb: 4,
        }}
      >
        {selectedDisplayName}:{" "}
        {t("generative:label.selectModelAndConfigureParameters")}
      </Typography>
      <Autocomplete
        disablePortal
        options={relatedComponents.map((t) => t.name)}
        onChange={(event, newValue) => {
          const selected = relatedComponents.find(
            (model) => model.name === newValue,
          );
          setSelectedModel(selected);
        }}
        sx={{ mb: 5 }}
        renderInput={(params) => <TextField {...params} label="Model" />}
        data-tour="model-selection"
      />
      {!selectedModel && (
        <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 1 }}>
          <Button variant="outlined" onClick={goToBackStep} sx={{ mr: 1 }}>
            {t("generative:button.backToTaskSelection")}
          </Button>
          <Button variant="contained" disabled>
            {t("generative:button.createSession")}
          </Button>
        </Box>
      )}

      {selectedModel && selectedModel.schema && (
        <form onSubmit={formik.handleSubmit}>
          <Box sx={{ mb: 5 }}>
            <Box width="60%">
              <Typography
                sx={{
                  fontSize: "16px",
                  whiteSpace: "normal",
                  wordBreak: "break-word",
                  mb: 2,
                }}
              >
                {t("common:parameters")}
              </Typography>
              <FormSchemaRenderFields
                modelSchema={processedProperties}
                formik={formik}
                autoSave={false}
                handleUpdateSchema={(updatedValues) => {
                  formik.setValues((prevValues) => ({
                    ...prevValues,
                    ...updatedValues,
                  }));
                }}
                onFormSubmit={formik.handleSubmit}
                setError={(error) => console.error(error)}
                errorsMessage={formik.errors}
              />
            </Box>
            <Typography
              sx={{
                fontSize: "16px",
                whiteSpace: "normal",
                wordBreak: "break-word",
                mb: 2,
              }}
            >
              {t("generative:label.nameYourSession")}
            </Typography>
            {/* Session name */}
            <TextField
              fullWidth
              label={t("generative:label.sessionName")}
              name="name"
              value={formik.values.name}
              onChange={handleNameInputChange}
              error={nameError}
              helperText={nameErrorMessage}
              sx={{ mb: 2 }}
            />
            {/* Session description */}
            <TextField
              fullWidth
              label={t("generative:label.sessionDescription")}
              name="description"
              value={formik.values.description}
              onChange={formik.handleChange}
              error={Boolean(formik.errors.description)}
              helperText={formik.errors.description}
              sx={{ mb: 2 }}
            />

            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                mt: 2,
              }}
            >
              <Button variant="outlined" onClick={goToBackStep} sx={{ mr: 1 }}>
                {t("generative:button.backToTaskSelection")}
              </Button>
              <Button type="submit" variant="contained">
                {t("generative:button.createSession")}
              </Button>
            </Box>
          </Box>
        </form>
      )}
    </Box>
  );
}
