import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { useFormik } from "formik";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import {
  createGenerativeSession,
  getRelatedComponents,
} from "../../api/generativeTask";
import { generateSequentialName } from "../../utils/nameGenerator";
import {
  buildYupSchema,
  formatTaskNameForSession,
  preprocessSchema,
} from "./utils";
import { useGenerative } from "./GenerativeContext";

const CreateSessionContext = createContext(null);

export const useCreateSession = () => useContext(CreateSessionContext);

export function CreateSessionProvider({ children }) {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["generative", "common"]);
  const {
    tasks,
    sessions: existingSessions,
    setSessions,
  } = useGenerative();

  const [step, setStep] = useState(0);
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [selectedModel, setSelectedModel] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Load all generative models grouped by their compatible task
  useEffect(() => {
    if (!tasks || tasks.length === 0) return;
    let cancelled = false;
    setLoadingModels(true);

    Promise.all(
      tasks.map((task) =>
        getRelatedComponents(task.name).then((components) =>
          components.map((c) => ({
            ...c,
            task_name: task.name,
            task_display_name: task.display_name || task.name,
          })),
        ),
      ),
    )
      .then((perTaskLists) => {
        if (cancelled) return;
        // Deduplicate by model name (a model may appear under several tasks).
        const seen = new Set();
        const flat = [];
        perTaskLists.flat().forEach((m) => {
          if (seen.has(m.name)) return;
          seen.add(m.name);
          flat.push(m);
        });
        setModels(flat);
      })
      .catch((err) => {
        console.error("Failed to load generative models", err);
        enqueueSnackbar(t("generative:error.failedToLoadModels"), {
          variant: "error",
        });
      })
      .finally(() => {
        if (!cancelled) setLoadingModels(false);
      });

    return () => {
      cancelled = true;
    };
  }, [tasks, enqueueSnackbar, t]);

  const defaultName = useMemo(() => {
    if (!selectedModel?.task_name) return "";
    const { defaultName: name } = generateSequentialName({
      base: `${formatTaskNameForSession(selectedModel.task_name)}_Session`,
      items: existingSessions,
      getName: (session) => session.name,
      filter: (session) => session.task_name === selectedModel.task_name,
    });
    return name;
  }, [selectedModel, existingSessions]);

  const processedProperties = useMemo(
    () =>
      selectedModel?.schema?.properties
        ? preprocessSchema(selectedModel.schema.properties)
        : {},
    [selectedModel],
  );

  const validationSchema = useMemo(
    () =>
      Object.keys(processedProperties).length > 0
        ? buildYupSchema(processedProperties)
        : null,
    [processedProperties],
  );

  const formik = useFormik({
    initialValues: { name: "", description: "" },
    validationSchema,
    enableReinitialize: false,
    validate: (values) => {
      const errors = {};
      if (!values.name || values.name.trim() === "") {
        errors.name = t("generative:error.nameRequired");
      }
      return errors;
    },
    onSubmit: async (values) => {
      if (!selectedModel) return;
      setSubmitting(true);
      try {
        const created = await createGenerativeSession({
          name: values.name,
          description: values.description,
          task_name: selectedModel.task_name,
          model_name: selectedModel.name,
          parameters: values,
        });
        setSessions((prev) => [...prev, created]);
        enqueueSnackbar(t("generative:message.sessionCreatedSuccess"), {
          variant: "success",
        });
        navigate(`/app/generative/sessions/${created.id}`);
      } catch (error) {
        console.error("Error creating session:", error);
        const detail = error?.response?.data?.detail || "";
        if (error?.response?.status === 409 || detail.includes("already exists")) {
          enqueueSnackbar(t("generative:error.sessionNameExists"), {
            variant: "error",
          });
        } else {
          enqueueSnackbar(t("generative:error.failedToCreateSession"), {
            variant: "error",
          });
        }
      } finally {
        setSubmitting(false);
      }
    },
  });

  // When a model is selected, seed formik with its parameter defaults + name
  const handleSelectModel = useCallback(
    (model) => {
      setSelectedModel(model);
      const props = model?.schema?.properties
        ? preprocessSchema(model.schema.properties)
        : {};
      const paramDefaults = Object.keys(props).reduce((acc, key) => {
        acc[key] = props[key].placeholder ?? "";
        return acc;
      }, {});
      formik.resetForm({
        values: {
          name: formik.values.name && formik.values.name.length > 0
            ? formik.values.name
            : "",
          description: formik.values.description || "",
          ...paramDefaults,
        },
      });
    },
    [],
  );

  // Once defaultName is known and formik.name is empty, fill it in
  useEffect(() => {
    if (!selectedModel) return;
    if (!formik.values.name && defaultName) {
      formik.setFieldValue("name", defaultName);
    }
  }, [defaultName, selectedModel]);

  const handleNext = () => {
    if (step === 0 && selectedModel) setStep(1);
  };

  const handleBack = () => {
    if (step === 1) setStep(0);
  };

  const handleCancel = () => {
    navigate("/app/generative");
  };

  const handleCreate = () => {
    formik.submitForm();
  };

  const value = {
    step,
    models,
    loadingModels,
    selectedModel,
    handleSelectModel,
    formik,
    processedProperties,
    submitting,
    handleNext,
    handleBack,
    handleCancel,
    handleCreate,
  };

  return (
    <CreateSessionContext.Provider value={value}>
      {children}
    </CreateSessionContext.Provider>
  );
}
