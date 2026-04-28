import { useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CenterBox from "../../../components/threeSectionLayout/panelContainers/CenterBox";
import DocumentSelector from "../../../components/generative/RAG/DocumentSelector";
import ChunkingSection from "./sections/ChunkingSection";
import RetrieverSection from "./sections/RetrieverSection";
import GeneratorSection from "./sections/GeneratorSection";
import PromptSection from "./sections/PromptSection";
import { useSnackbar } from "notistack";
import { createRAGSession } from "../../../api/rag";
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
    prompt_id: null,
  },
};

export default function SimplifiedSessionSetup({
  initialData,
  onClose,
  onSessionCreated,
  existingSessions = [],
}) {
  const { enqueueSnackbar } = useSnackbar();
  const suggestedName = useMemo(() => {
    const sessionsList = Array.isArray(existingSessions) ? existingSessions : [];
    console.log("Existing sessions passed to SimplifiedSessionSetup:", sessionsList);
    
    // Filter sessions by task name
    const ragSessions = sessionsList.filter(s => s?.task_name === "RAGTask");
    console.log("Existing RAG Sessions for Name Generation:", ragSessions);
    
    const { defaultName } = generateSequentialName({
      base: "RAG_Session",
      items: ragSessions,
      getName: (session) => session?.name,
      // The filter is already applied above for clarity
    });

    return defaultName || "RAG_Session_1";
  }, [existingSessions]);

  const lastSuggestedNameRef = useRef(suggestedName);
  const [isNameTouched, setIsNameTouched] = useState(Boolean(initialData?.name));
  const [sessionData, setSessionData] = useState({
    ...defaultSessionData,
    name: initialData?.name || suggestedName,
    description: initialData?.description || "",
    documents: initialData?.documents || [],
  });
  const [saving, setSaving] = useState(false);
  const [nameError, setNameError] = useState("");
  const [expandedSections, setExpandedSections] = useState({
    chunking: true,
    retriever: true,
    generator: true,
    prompt: true,
  });

  useEffect(() => {
    if (initialData?.name) return;
    if (isNameTouched) return;

    setSessionData((prev) => {
      const currentName = prev?.name || "";
      const lastSuggested = lastSuggestedNameRef.current;

      const shouldReplace =
        currentName.trim() === "" || currentName === lastSuggested;
      if (!shouldReplace) {
        lastSuggestedNameRef.current = suggestedName;
        return prev;
      }

      lastSuggestedNameRef.current = suggestedName;
      return { ...prev, name: suggestedName };
    });
  }, [initialData?.name, isNameTouched, suggestedName]);

  const handleSessionNameChange = (event) => {
    const value = event.target.value;
    setIsNameTouched(true);
    setSessionData((prev) => ({
      ...prev,
      name: value,
    }));

    if (value.trim() === "") {
      setNameError("Session name cannot be empty");
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

  const handleDocumentSelectionChange = (selectedDocs) => {
    setSessionData((prev) => ({
      ...prev,
      documents: selectedDocs.map((doc) => doc.id),
    }));
  };

  const updateChunkingModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        chunking_model: model,
      },
    }));
  };

  const updateRetrieverModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        retriever_model: model,
      },
    }));
  };

  const updateGeneratorModel = (model) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        generator_model: model,
      },
    }));
  };

  const updatePromptId = (promptId) => {
    setSessionData((prev) => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        prompt_id: promptId,
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
      enqueueSnackbar("Session name is required", { variant: "warning" });
      return false;
    }
    if (sessionData.documents.length === 0) {
      enqueueSnackbar("At least one document must be selected", {
        variant: "warning",
      });
      return false;
    }
    if (!sessionData.parameters.chunking_model?.component) {
      enqueueSnackbar("Chunking model must be configured", { variant: "warning" });
      return false;
    }
    if (!sessionData.parameters.retriever_model?.component) {
      enqueueSnackbar("Retriever model must be configured", { variant: "warning" });
      return false;
    }
    if (!sessionData.parameters.generator_model?.component) {
      enqueueSnackbar("Generator model must be configured", { variant: "warning" });
      return false;
    }
    if (!sessionData.parameters.prompt_id) {
      enqueueSnackbar("Prompt template must be selected", { variant: "warning" });
      return false;
    }
    return true;
  };

  const isConfigurationComplete = useMemo(() => {
    const isNameValid = Boolean(sessionData.name?.trim());
    const areDocsValid = Array.isArray(sessionData.documents) && sessionData.documents.length > 0;
    const isChunkingValid = Boolean(sessionData.parameters.chunking_model?.component);
    const isRetrieverValid = Boolean(sessionData.parameters.retriever_model?.component);
    const isGeneratorValid = Boolean(sessionData.parameters.generator_model?.component);
    const isPromptValid = sessionData.parameters.prompt_id !== null && sessionData.parameters.prompt_id !== undefined;

    const complete = isNameValid && areDocsValid && isChunkingValid && isRetrieverValid && isGeneratorValid && isPromptValid;
    
    if (!complete) {
      console.log("RAG Configuration Incomplete:", {
        isNameValid,
        areDocsValid,
        isChunkingValid,
        isRetrieverValid,
        isGeneratorValid,
        isPromptValid,
        sessionData
      });
    }

    return complete;
  }, [sessionData]);

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
          prompt_id: sessionData.parameters.prompt_id,
        },
      };

      const createdSession = await createRAGSession(finalSessionData);
      enqueueSnackbar("RAG Session created successfully", { variant: "success" });

      if (onSessionCreated) {
        onSessionCreated(createdSession);
      } else {
        onClose?.();
      }
    } catch (error) {
      console.error("Error creating RAG session:", error);
      enqueueSnackbar(
        error.message || "Error creating RAG session",
        { variant: "error" }
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <CenterBox>
      <Box
        display="flex"
        flexDirection="column"
        gap={3}
        width="100%"
      >
        {/* Header */}
        <Box>
          <Typography variant="h5" component="h1" sx={{ mb: 1 }}>
            Create RAG Session
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Provide basic information, select documents, and configure the
            components for your RAG session.
          </Typography>
        </Box>

        {/* Session Details */}
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 3, fontWeight: 600 }}>
            Session Details
          </Typography>

          <Box display="flex" flexDirection="column" gap={2}>
            <TextField
              fullWidth
              label="Session Name *"
              variant="outlined"
              value={sessionData.name}
              onChange={handleSessionNameChange}
              placeholder="e.g., Product Documentation RAG"
              error={Boolean(nameError)}
              helperText={nameError}
              inputProps={{ maxLength: 256 }}
              size="medium"
              disabled={saving}
            />

            <TextField
              fullWidth
              label="Description (Optional)"
              variant="outlined"
              value={sessionData.description}
              onChange={handleSessionDescriptionChange}
              placeholder="Describe the purpose of this RAG session..."
              multiline
              rows={3}
              inputProps={{ maxLength: 512 }}
              size="medium"
              disabled={saving}
            />
          </Box>
        </Box>

        {/* Document Selection */}
        <Box display="flex" flexDirection="column" gap={1}>
          <Typography variant="subtitle1">Select Documents</Typography>
          <Typography variant="body2" color="textSecondary">
            Upload new documents or select from existing ones to be used for RAG.
          </Typography>

          <Box
            width="100%"
            sx={{
              display: "flex",
              flexDirection: "column",
              minHeight: "500px",
            }}
          >
            <DocumentSelector
              selectedIds={[...sessionData.documents]}
              onSelect={handleDocumentSelectionChange}
            />
          </Box>
        </Box>

        {/* Configuration Sections */}
        <Box display="flex" flexDirection="column" gap={2}>
          {/* Chunking Section */}
          <Accordion
            expanded={expandedSections.chunking}
            onChange={handleSectionChange("chunking")}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                Chunking Strategy
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
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
                Retriever Model
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <RetrieverSection
                retrieverModel={sessionData.parameters.retriever_model}
                setRetrieverModel={updateRetrieverModel}
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
                Language Model (LLM)
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <GeneratorSection
                generatorModel={sessionData.parameters.generator_model}
                setGeneratorModel={updateGeneratorModel}
              />
            </AccordionDetails>
          </Accordion>

          {/* Prompt Section */}
          <Accordion
            expanded={expandedSections.prompt}
            onChange={handleSectionChange("prompt")}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                Prompt Template
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <PromptSection
                promptId={sessionData.parameters.prompt_id}
                setPromptId={updatePromptId}
              />
            </AccordionDetails>
          </Accordion>
        </Box>

        {/* Action Buttons */}
        <Box
          display="flex"
          justifyContent="flex-end"
          gap={2}
          sx={{ pt: 2, borderTop: "1px solid", borderColor: "divider" }}
        >
          <Button
            variant="outlined"
            color="inherit"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSave}
            disabled={saving || !isConfigurationComplete}
            sx={{ minWidth: 120 }}
          >
            {saving ? <CircularProgress size={20} /> : "Save Session"}
          </Button>
        </Box>
      </Box>
    </CenterBox>
  );
}
