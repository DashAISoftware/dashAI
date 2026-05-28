import { useEffect, useMemo, useState, useCallback } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  IconButton,
  Tooltip,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { ViewList as ViewListIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import DocumentSelector from "../../../components/generative/RAG/DocumentSelector";
import ChunkingSection from "./sections/ChunkingSection";
import RetrieverSection from "./sections/RetrieverSection";
import GeneratorSection from "./sections/GeneratorSection";
import PromptSection from "./sections/PromptSection";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { createRAGSession } from "../../../api/rag";
import { getSessions } from "../../../api/session";
import { generateSequentialName } from "../../../utils/nameGenerator";

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
    generator_model: {
      component: "",
      params: {},
    },
    prompt: {
      component: "",
      params: {},
    },
  },
};

export default function SimplifiedSessionSetup({
  initialData,
  onClose,
  onSessionCreated,
  existingSessions = [],
}) {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["generative"]);
  const navigate = useNavigate();
  const goToPromptsDetail = () => navigate("/app/generative/rag/prompts");
  const goToDocumentsDetail = () => navigate("/app/generative/rag/documents");

  const [suggestedName, setSuggestedName] = useState(() => {
    const sessionsList = Array.isArray(existingSessions) ? existingSessions : [];
    const ragSessions = sessionsList.filter(s => s?.task_name === "RAGTask");
    const { defaultName } = generateSequentialName({
      base: "RAG_Session",
      items: ragSessions,
      getName: (session) => session?.name,
    });
    return defaultName || "RAG_Session_1";
  });

  useEffect(() => {
    let cancelled = false;
    getSessions().then((allSessions) => {
      if (cancelled) return;
      const ragSessions = (allSessions || []).filter(s => s?.task_name === "RAGTask");
      const { defaultName } = generateSequentialName({
        base: "RAG_Session",
        items: ragSessions,
        getName: (session) => session?.name,
      });
      setSuggestedName(defaultName || "RAG_Session_1");
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const [isNameTouched, setIsNameTouched] = useState(Boolean(initialData?.name));
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

  // Directly derive values from state to ensure reactivity
  let chunkSize = sessionData.parameters.chunking_model?.params?.chunk_size || 0;
  // If chunking model is character based, use 1 token = 4 characters as a rough estimate
  if (sessionData.parameters.chunking_model?.component?.toLowerCase().includes("character")) {
    chunkSize = Math.ceil(chunkSize / 4);
  }
  const topK = sessionData.parameters.retriever_model?.params?.top_k || 0;

  const [promptTokenCount, setPromptTokenCount] = useState(0);

  // Update name if suggestedName changes and user hasn't touched the field
  useEffect(() => {
    if (initialData?.name) return;
    if (isNameTouched) return;
    setSessionData((prev) => ({ ...prev, name: suggestedName }));
  }, [initialData?.name, isNameTouched, suggestedName]);

  // Handle name duplicate check when existingSessions or name changes
  useEffect(() => {
    const trimmedValue = sessionData.name.trim().toLowerCase();
    if (!trimmedValue) {
      setIsDuplicateName(false);
      return;
    }

    const sessionsList = Array.isArray(existingSessions) ? existingSessions : [];
    const isDuplicate = sessionsList.some(
      (session) => session?.name?.toLowerCase() === trimmedValue
    );
    setIsDuplicateName(isDuplicate);
  }, [sessionData.name, existingSessions]);

  const handleSessionNameChange = (event) => {
    const value = event.target.value;
    setIsNameTouched(true);
    setSessionData((prev) => ({
      ...prev,
      name: value,
    }));

    // Validate empty name
    if (value.trim() === "") {
      setNameError(t("generative:simplifiedRag.validation.nameRequired"));
    } else {
      setNameError("");
    }
  };

  const handleSessionDescriptionChange = (event) => {
    const value = event.target.value;
    setSessionData((prev) => ({
      ...prev,
      description: value,
    }));
  };

  const handleDocumentSelectionChange = useCallback((selectedDocs) => {
    setSessionData((prev) => ({
      ...prev,
      documents: selectedDocs.map((doc) => doc.id),
    }));
  }, []);

  const updateChunkingModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        chunking_model: { ...model },
      },
    }));
  };

  const updateRetrieverModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        retriever_model: { ...model },
      },
    }));
  };

  const updateGeneratorModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        generator_model: { ...model },
      },
    }));
  };

  const updatePrompt = (prompt) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        prompt,
      },
    }));
  };

  const handleSectionChange = (section) => (event, isExpanded) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: isExpanded,
    }));
  };

  const validateConfiguration = () => {
    if (!sessionData.name.trim()) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.nameRequired"), { variant: "warning" });
      return false;
    }
    if (isDuplicateName) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.nameUnique"), { variant: "warning" });
      return false;
    }
    if (sessionData.documents.length === 0) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.documentsRequired"), {
        variant: "warning",
      });
      return false;
    }
    if (!sessionData.parameters.chunking_model?.component) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.chunkingRequired"), { variant: "warning" });
      return false;
    }
    if (!sessionData.parameters.retriever_model?.component) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.retrieverRequired"), { variant: "warning" });
      return false;
    }
    if (!sessionData.parameters.generator_model?.component) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.generatorRequired"), { variant: "warning" });
      return false;
    }
    if (!isGeneratorValidState) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.generatorInvalid"), { variant: "error" });
      return false;
    }
    if (!sessionData.parameters.prompt?.component) {
      enqueueSnackbar(t("generative:simplifiedRag.validation.promptRequired"), { variant: "warning" });
      return false;
    }
    return true;
  };

  const isConfigurationComplete = useMemo(() => {
    const isNameValid = Boolean(sessionData.name?.trim()) && !isDuplicateName;
    const areDocsValid = Array.isArray(sessionData.documents) && sessionData.documents.length > 0;
    const isChunkingValid = Boolean(sessionData.parameters.chunking_model?.component);
    const isRetrieverValid = Boolean(sessionData.parameters.retriever_model?.component);
    const isPromptValid = sessionData.parameters.prompt?.component;

    return isNameValid && areDocsValid && isChunkingValid && isRetrieverValid && isGeneratorValidState && isPromptValid;
  }, [sessionData, isGeneratorValidState, isDuplicateName]);

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
          generation_model: sessionData.parameters.generator_model,
          prompt: sessionData.parameters.prompt,
        },
      };

      const createdSession = await createRAGSession(finalSessionData);
      enqueueSnackbar(t("generative:simplifiedRag.messages.success"), { variant: "success" });

      if (onSessionCreated) {
        onSessionCreated(createdSession);
      } else {
        onClose?.();
      }
    } catch (error) {
      console.error("Error creating RAG session:", error);
      enqueueSnackbar(
        error.message || t("generative:error.failedToCreateSession"),
        { variant: "error" }
      );
    } finally {
      setSaving(false);
    }
  };

  return (
      <Box
        width="100%"
        height="100%"
        display="flex"
        flexDirection="column"
        sx={{ px: 2, pt: 2, pb: 0 }}
      >
        <Box
          display="flex"
          flexDirection="column"
          height="100%"
          width="100%"
        >
        {/* Header */}
        <Box flexShrink={0}>
          <Typography variant="h5" component="h1" sx={{ mb: 1 }}>
            {t("generative:simplifiedRag.setup.title")}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {t("generative:simplifiedRag.setup.subtitle")}
          </Typography>
        </Box>

        {/* Scrollable Content */}
        <Box flex={1} overflow="auto" sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 3 }}>

        {/* Session Details */}
        <Accordion
          expanded={expandedSections.sessionDetails}
          onChange={handleSectionChange("sessionDetails")}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {t("generative:simplifiedRag.setup.sessionDetails")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            sx={{ display: "flex", flexDirection: "column", gap: 2, px: 4 }}
          >
            <TextField
              fullWidth
              label={t("generative:simplifiedRag.setup.sessionName")}
              variant="outlined"
              value={sessionData.name}
              onChange={handleSessionNameChange}
              placeholder={t("generative:simplifiedRag.setup.sessionNamePlaceholder")}
              error={Boolean(nameError) || isDuplicateName}
              helperText={nameError || (isDuplicateName ? t("generative:simplifiedRag.setup.sessionNameDuplicate") : "")}
              inputProps={{ maxLength: 256 }}
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
                  {t("generative:simplifiedRag.setup.sessionNameDuplicateAlert")}
                </Typography>
              </Alert>
            )}

            <TextField
              fullWidth
              label={t("generative:simplifiedRag.setup.description")}
              variant="outlined"
              value={sessionData.description}
              onChange={handleSessionDescriptionChange}
              placeholder={t("generative:simplifiedRag.setup.descriptionPlaceholder")}
              multiline
              rows={3}
              inputProps={{ maxLength: 512 }}
              size="medium"
              disabled={saving}
            />
          </AccordionDetails>
        </Accordion>

        {/* Document Selection */}
        <Accordion
          expanded={expandedSections.documents}
          onChange={handleSectionChange("documents")}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", mr: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {t("generative:simplifiedRag.setup.selectDocuments")}
              </Typography>
              <Tooltip title={t("generative:simplifiedRag.setup.openDocumentsLibrary")}>
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); goToDocumentsDetail(); }}
                  aria-label="open-documents-library"
                >
                  <ViewListIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </AccordionSummary>
          <AccordionDetails
            sx={{ display: "flex", flexDirection: "column", gap: 2, px: 4 }}
          >
            <Typography variant="body2" color="textSecondary">
              {t("generative:simplifiedRag.setup.selectDocumentsDescription")}
            </Typography>

            <Box width="100%">
              <DocumentSelector
                selectedIds={sessionData.documents}
                onSelect={handleDocumentSelectionChange}
              />
            </Box>
          </AccordionDetails>
        </Accordion>

        {/* Configuration Sections */}
        <Box display="flex" flexDirection="column" gap={2}>
          {/* Chunking Section */}
          <Accordion
            expanded={expandedSections.chunking}
            onChange={handleSectionChange("chunking")}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {t("generative:simplifiedRag.setup.chunkingStrategy")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2, px: 4 }}
            >
              <ChunkingSection
                chunkingModel={sessionData.parameters.chunking_model}
                setChunkingModel={updateChunkingModel}
              />
            </AccordionDetails>
          </Accordion>

          {/* Retriever Section */}
          <Accordion
            expanded={expandedSections.retriever}
            onChange={handleSectionChange("retriever")}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {t("generative:simplifiedRag.setup.retrieverModel")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2, px: 4 }}
            >
              <RetrieverSection
                retrieverModel={sessionData.parameters.retriever_model}
                setRetrieverModel={updateRetrieverModel}
              />
            </AccordionDetails>
          </Accordion>

          {/* Prompt Section */}
          <Accordion
            expanded={expandedSections.prompt}
            onChange={handleSectionChange("prompt")}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", mr: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {t("generative:simplifiedRag.setup.promptTemplate")}
                </Typography>
                <Tooltip title={t("generative:simplifiedRag.prompt.openPrompts")}>
                  <IconButton
                    size="small"
                    onClick={(e) => { e.stopPropagation(); goToPromptsDetail(); }}
                    aria-label="open-prompt-library"
                  >
                    <ViewListIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2, px: 4 }}
            >
              <PromptSection
                promptModel={sessionData.parameters.prompt}
                setPromptModel={updatePrompt}
                onTokenCountChange={setPromptTokenCount}
              />
            </AccordionDetails>
          </Accordion>

          {/* Generator Section */}
          <Accordion
            expanded={expandedSections.generator}
            onChange={handleSectionChange("generator")}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {t("generative:simplifiedRag.setup.languageModel")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2, px: 4 }}
            >
              <GeneratorSection
                generatorModel={sessionData.parameters.generator_model}
                setGeneratorModel={updateGeneratorModel}
                chunkSize={chunkSize}
                topK={topK}
                promptTokenCount={promptTokenCount}
                setIsValid={setIsGeneratorValidState}
              />
            </AccordionDetails>
          </Accordion>

        </Box>
        </Box>

        {/* Action Buttons — fixed at bottom */}
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
            {t("generative:simplifiedRag.setup.cancel")}
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSave}
            disabled={saving || !isConfigurationComplete}
            sx={{ minWidth: 120 }}
          >
            {saving ? <CircularProgress size={20} /> : t("generative:simplifiedRag.setup.saveSession")}
          </Button>
        </Box>
      </Box>
      </Box>
    );
}
