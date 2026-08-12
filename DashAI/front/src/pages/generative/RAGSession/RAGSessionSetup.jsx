import { useEffect, useMemo, useState, useCallback } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  CircularProgress,
  Alert,
} from "@mui/material";
import { ViewList as ViewListIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import DocumentSelector from "../../../components/generative/RAG/DocumentSelector";
import ChunkingSection from "./sections/ChunkingSection";
import RetrieverSection from "./sections/RetrieverSection";
import GeneratorSection from "./sections/GeneratorSection";
import PromptSection from "./sections/PromptSection";
import RAGCard from "./components/RAGCard";
import SectionCard from "./components/SectionCard";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { createRAGSession } from "../../../api/rag";
import { getSessions } from "../../../api/session";
import { generateSequentialName } from "../../../utils/nameGenerator";
import { validateModelConfig } from "../../../utils/ragValidation";
import RAGSectionColumn from "./components/RAGSectionColumn";

const defaultSessionData = {
  name: "",
  description: "",
  documents: [],
  parameters: {
    chunking_model: {
      component: "",
      params: {},
    },
    retriever_model: {
      component: "",
      params: {},
    },
    generation_model: {
      component: "",
      params: {},
    },
    prompt: {
      component: "",
      params: {},
    },
  },
};

/**
 * RAG session creation wizard.
 * Composes document, chunking, retriever, generator, and prompt
 * sections into a multi-card accordion form and creates the session
 * via the API.
 *
 * @param {object}   props
 * @param {object}   [props.initialData]      - Pre-populated session data for editing.
 * @param {Function} [props.onClose]           - Called when the user cancels or closes.
 * @param {Function} [props.onSessionCreated]  - Called after a successful session create.
 * @param {Array}    [props.existingSessions]  - Existing sessions for duplicate-name check.
 * @returns {JSX.Element} The setup wizard.
 */
export default function RAGSessionSetup({
  initialData,
  onClose,
  onSessionCreated,
  existingSessions = [],
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["generative"]);
  const navigate = useNavigate();
  const goToPromptsDetail = () => navigate("/app/generative/RAG/prompts");
  const goToDocumentsDetail = () => navigate("/app/generative/RAG/documents");

  const [suggestedName, setSuggestedName] = useState(() => {
    const sessionsList = Array.isArray(existingSessions)
      ? existingSessions
      : [];
    const ragSessions = sessionsList.filter((s) => s?.task_name === "RAGTask");
    const { defaultName } = generateSequentialName({
      base: "RAG_Session",
      items: ragSessions,
      getName: (session) => session?.name,
    });
    return defaultName || "RAG_Session_1";
  });

  useEffect(() => {
    let cancelled = false;
    getSessions()
      .then((allSessions) => {
        if (cancelled) return;
        const ragSessions = (allSessions || []).filter(
          (s) => s?.task_name === "RAGTask",
        );
        const { defaultName } = generateSequentialName({
          base: "RAG_Session",
          items: ragSessions,
          getName: (session) => session?.name,
        });
        setSuggestedName(defaultName || "RAG_Session_1");
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const [isNameTouched, setIsNameTouched] = useState(
    Boolean(initialData?.name),
  );
  const [sessionData, setSessionData] = useState({
    ...defaultSessionData,
    name: initialData?.name || suggestedName,
    description: initialData?.description || "",
    documents: initialData?.documents || [],
  });
  const [saving, setSaving] = useState(false);
  const [nameError, setNameError] = useState("");
  const [isDuplicateName, setIsDuplicateName] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    sessionDetails: true,
    documents: true,
    chunking: true,
    retriever: true,
    generator: true,
    prompt: true,
  });

  const [isGeneratorValidState, setIsGeneratorValidState] = useState(false);

  let chunkSize =
    sessionData.parameters.chunking_model?.params?.chunk_size || 0;
  // If chunking model is character based, use 1 token = 4 characters as a rough estimate
  if (
    sessionData.parameters.chunking_model?.component
      ?.toLowerCase()
      .includes("character")
  ) {
    chunkSize = Math.ceil(chunkSize / 4);
  }
  const topK = sessionData.parameters.retriever_model?.params?.top_k || 0;

  const [promptTokenCount, setPromptTokenCount] = useState(0);

  useEffect(() => {
    if (initialData?.name) return;
    if (isNameTouched) return;
    setSessionData((prev) => ({ ...prev, name: suggestedName }));
  }, [initialData?.name, isNameTouched, suggestedName]);

  useEffect(() => {
    const trimmedValue = sessionData.name.trim().toLowerCase();
    if (!trimmedValue) {
      setIsDuplicateName(false);
      return;
    }

    const sessionsList = Array.isArray(existingSessions)
      ? existingSessions
      : [];
    const isDuplicate = sessionsList.some(
      (session) => session?.name?.toLowerCase() === trimmedValue,
    );
    setIsDuplicateName(isDuplicate);
  }, [sessionData.name, existingSessions]);

  /**
   * Update the session name and validate it is non-empty.
   * @param {object} event - Input change event.
   */
  const handleSessionNameChange = (event) => {
    const value = event.target.value;
    setIsNameTouched(true);
    setSessionData((prev) => ({
      ...prev,
      name: value,
    }));

    if (value.trim() === "") {
      setNameError(t("generative:rag.validation.nameRequired"));
    } else {
      setNameError("");
    }
  };

  /**
   * Update the session description.
   * @param {object} event - Input change event.
   */
  const handleSessionDescriptionChange = (event) => {
    const value = event.target.value;
    setSessionData((prev) => ({
      ...prev,
      description: value,
    }));
  };

  /**
   * Store only the document IDs when the user changes the document selection.
   * @param {Array} selectedDocs - Array of document objects with `id`.
   */
  const handleDocumentSelectionChange = useCallback((selectedDocs) => {
    setSessionData((prev) => ({
      ...prev,
      documents: selectedDocs.map((doc) => doc.id),
    }));
  }, []);

  /**
   * Replace the chunking model configuration.
   * @param {object} model - { component, params } for the chunker.
   */
  const updateChunkingModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        chunking_model: { ...model },
      },
    }));
  };

  /**
   * Replace the retriever model configuration.
   * @param {object} model - { component, params } for the retriever.
   */
  const updateRetrieverModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        retriever_model: { ...model },
      },
    }));
  };

  /**
   * Replace the generation model configuration.
   * @param {object} model - { component, params } for the generator.
   */
  const updateGeneratorModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        generation_model: { ...model },
      },
    }));
  };

  /**
   * Replace the prompt configuration.
   * @param {object} prompt - { component, params } for the prompt.
   */
  const updatePrompt = (prompt) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        prompt,
      },
    }));
  };

  /**
   * Return a handler that toggles the expanded state for a given accordion section.
   * @param {string} section - Section key (e.g. "chunking", "retriever").
   * @returns {Function} Event handler for the accordion onChange.
   */
  const handleSectionChange = (section) => (event, isExpanded) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: isExpanded,
    }));
  };

  /**
   * Validate all required configuration fields before saving.
   * Shows snackbar warnings for each missing/invalid field.
   * @returns {boolean} True if the configuration is valid.
   */
  const validateConfiguration = () => {
    if (!sessionData.name.trim()) {
      enqueueSnackbar(t("generative:rag.validation.nameRequired"), {
        variant: "warning",
      });
      return false;
    }
    if (isDuplicateName) {
      enqueueSnackbar(t("generative:rag.validation.nameUnique"), {
        variant: "warning",
      });
      return false;
    }
    if (sessionData.documents.length === 0) {
      enqueueSnackbar(t("generative:rag.validation.documentsRequired"), {
        variant: "warning",
      });
      return false;
    }
    if (!sessionData.parameters.chunking_model?.component) {
      enqueueSnackbar(t("generative:rag.validation.chunkingRequired"), {
        variant: "warning",
      });
      return false;
    }
    if (!sessionData.parameters.retriever_model?.component) {
      enqueueSnackbar(t("generative:rag.validation.retrieverRequired"), {
        variant: "warning",
      });
      return false;
    }
    if (!sessionData.parameters.generation_model?.component) {
      enqueueSnackbar(t("generative:rag.validation.generatorRequired"), {
        variant: "warning",
      });
      return false;
    }
    if (!isGeneratorValidState) {
      enqueueSnackbar(t("generative:rag.validation.generatorInvalid"), {
        variant: "error",
      });
      return false;
    }
    if (!sessionData.parameters.prompt?.component) {
      enqueueSnackbar(t("generative:rag.validation.promptRequired"), {
        variant: "warning",
      });
      return false;
    }

    const chunkingValidation = validateModelConfig(
      sessionData.parameters.chunking_model,
      t,
    );
    if (!chunkingValidation.valid) {
      chunkingValidation.errors.forEach((err) =>
        enqueueSnackbar(err, { variant: "warning" }),
      );
      return false;
    }

    const retrieverValidation = validateModelConfig(
      sessionData.parameters.retriever_model,
      t,
    );
    if (!retrieverValidation.valid) {
      retrieverValidation.errors.forEach((err) =>
        enqueueSnackbar(err, { variant: "warning" }),
      );
      return false;
    }

    const generatorValidation = validateModelConfig(
      sessionData.parameters.generation_model,
      t,
    );
    if (!generatorValidation.valid) {
      generatorValidation.errors.forEach((err) =>
        enqueueSnackbar(err, { variant: "warning" }),
      );
      return false;
    }

    const promptValidation = validateModelConfig(
      sessionData.parameters.prompt,
      t,
    );
    if (!promptValidation.valid) {
      promptValidation.errors.forEach((err) =>
        enqueueSnackbar(err, { variant: "warning" }),
      );
      return false;
    }

    return true;
  };

  const isConfigurationComplete = useMemo(() => {
    const isNameValid = Boolean(sessionData.name?.trim()) && !isDuplicateName;
    const areDocsValid =
      Array.isArray(sessionData.documents) && sessionData.documents.length > 0;
    const isChunkingValid = Boolean(
      sessionData.parameters.chunking_model?.component,
    );
    const isRetrieverValid = Boolean(
      sessionData.parameters.retriever_model?.component,
    );
    const isGeneratorSelected = Boolean(
      sessionData.parameters.generation_model?.component,
    );
    const isPromptValid = sessionData.parameters.prompt?.component;

    return (
      isNameValid &&
      areDocsValid &&
      isChunkingValid &&
      isRetrieverValid &&
      isGeneratorValidState &&
      isGeneratorSelected &&
      isPromptValid
    );
  }, [sessionData, isGeneratorValidState, isDuplicateName]);

  /**
   * Validate and persist the RAG session via the API.
   * Navigates to the created session on success.
   */
  const handleSave = async () => {
    if (!validateConfiguration()) {
      return;
    }

    setSaving(true);
    try {
      const finalSessionData = {
        name: sessionData.name.trim(),
        description: sessionData.description.trim(),
        task_name: "RAGTask",
        model_name: "RAGPipeline",
        parameters: {
          documents: sessionData.documents,
          chunking_model: sessionData.parameters.chunking_model,
          retriever_model: sessionData.parameters.retriever_model,
          generation_model: sessionData.parameters.generation_model,
          prompt: sessionData.parameters.prompt,
        },
      };

      const createdSession = await createRAGSession(finalSessionData);
      enqueueSnackbar(t("generative:rag.messages.success"), {
        variant: "success",
      });

      if (onSessionCreated) {
        onSessionCreated(createdSession);
      } else {
        onClose?.();
      }
    } catch (error) {
      console.error("Error creating RAG session:", error);
      enqueueSnackbar(
        error.message || t("generative:error.failedToCreateSession"),
        { variant: "error" },
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box width="100%" height="100%" display="flex" flexDirection="column">
      <Box
        flex={1}
        overflow="auto"
        sx={{ display: "flex", flexDirection: "column", gap: 3 }}
      >
        <RAGSectionColumn>
          <Typography variant="h5" component="h3">
            {t("generative:rag.setup.title")}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {t("generative:rag.setup.subtitle")}
          </Typography>
        </RAGSectionColumn>

        <RAGCard
          title={t("generative:rag.setup.sessionDetails")}
          expanded={expandedSections.sessionDetails}
          onChange={handleSectionChange("sessionDetails")}
        >
          <SectionCard>
            <RAGSectionColumn>
              <TextField
                fullWidth
                label={t("generative:rag.setup.sessionName")}
                variant="outlined"
                value={sessionData.name}
                onChange={handleSessionNameChange}
                placeholder={t("generative:rag.setup.sessionNamePlaceholder")}
                error={Boolean(nameError) || isDuplicateName}
                helperText={
                  nameError ||
                  (isDuplicateName
                    ? t("generative:rag.setup.sessionNameDuplicate")
                    : "")
                }
                size="medium"
                disabled={saving}
              />

              {isDuplicateName && (
                <Alert
                  severity="warning"
                  sx={{
                    p: 2,
                    backgroundColor: "action.hover",
                    border: "1px solid",
                    borderColor: "warning.main",
                    borderRadius: 1,
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                  }}
                >
                  <Typography variant="body2">
                    {t("generative:rag.setup.sessionNameDuplicateAlert")}
                  </Typography>
                </Alert>
              )}

              <TextField
                fullWidth
                label={t("generative:rag.setup.description")}
                variant="outlined"
                value={sessionData.description}
                onChange={handleSessionDescriptionChange}
                placeholder={t("generative:rag.setup.descriptionPlaceholder")}
                multiline
                rows={3}
                size="medium"
                disabled={saving}
              />
            </RAGSectionColumn>
          </SectionCard>
        </RAGCard>

        <RAGCard
          title={t("generative:rag.setup.selectDocuments")}
          expanded={expandedSections.documents}
          onChange={handleSectionChange("documents")}
          actions={[
            {
              icon: <ViewListIcon fontSize="small" />,
              tooltip: t("generative:rag.setup.openDocumentsLibrary"),
              onClick: goToDocumentsDetail,
              ariaLabel: "open-documents-library",
            },
          ]}
        >
          <SectionCard>
            <DocumentSelector
              selectedIds={sessionData.documents}
              onSelect={handleDocumentSelectionChange}
            />
          </SectionCard>
        </RAGCard>

        <RAGCard
          title={t("generative:rag.setup.chunkingStrategy")}
          expanded={expandedSections.chunking}
          onChange={handleSectionChange("chunking")}
        >
          <SectionCard>
            <ChunkingSection
              chunkingModel={sessionData.parameters.chunking_model}
              setChunkingModel={updateChunkingModel}
            />
          </SectionCard>
        </RAGCard>

        <RAGCard
          title={t("generative:rag.setup.retrieverModel")}
          expanded={expandedSections.retriever}
          onChange={handleSectionChange("retriever")}
        >
          <SectionCard>
            <RetrieverSection
              retrieverModel={sessionData.parameters.retriever_model}
              setRetrieverModel={updateRetrieverModel}
            />
          </SectionCard>
        </RAGCard>

        <RAGCard
          title={t("generative:rag.setup.promptTemplate")}
          expanded={expandedSections.prompt}
          onChange={handleSectionChange("prompt")}
          actions={[
            {
              icon: <ViewListIcon fontSize="small" />,
              tooltip: t("generative:rag.prompt.openPrompts"),
              onClick: goToPromptsDetail,
              ariaLabel: "open-prompt-library",
            },
          ]}
        >
          <SectionCard>
            <PromptSection
              promptModel={sessionData.parameters.prompt}
              setPromptModel={updatePrompt}
              onTokenCountChange={setPromptTokenCount}
            />
          </SectionCard>
        </RAGCard>

        <RAGCard
          title={t("generative:rag.setup.languageModel")}
          expanded={expandedSections.generator}
          onChange={handleSectionChange("generator")}
        >
          <SectionCard>
            <GeneratorSection
              generatorModel={sessionData.parameters.generation_model}
              setGeneratorModel={updateGeneratorModel}
              chunkSize={chunkSize}
              topK={topK}
              promptTokenCount={promptTokenCount}
              setIsValid={setIsGeneratorValidState}
            />
          </SectionCard>
        </RAGCard>
      </Box>

      <Box
        flexShrink={0}
        display="flex"
        justifyContent="flex-end"
        gap={2}
        sx={{
          pt: 2,
          pb: 0,
          borderTop: "1px solid",
          borderColor: "divider",
        }}
      >
        <Button
          variant="outlined"
          color="inherit"
          onClick={onClose}
          disabled={saving}
        >
          {t("generative:rag.setup.cancel")}
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSave}
          disabled={saving || !isConfigurationComplete}
          sx={{ minWidth: 120 }}
        >
          {saving ? (
            <CircularProgress size={20} />
          ) : (
            t("generative:rag.setup.saveSession")
          )}
        </Button>
      </Box>
    </Box>
  );
}
