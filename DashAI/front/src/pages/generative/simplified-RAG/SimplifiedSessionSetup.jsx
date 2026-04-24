import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Typography,
  Paper,
  Divider,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CenterBox from "../../../components/threeSectionLayout/panelContainers/CenterBox";
import ChunkingSection from "./sections/ChunkingSection";
import RetrieverSection from "./sections/RetrieverSection";
import GeneratorSection from "./sections/GeneratorSection";
import PromptSection from "./sections/PromptSection";
import { useSnackbar } from "notistack";
import { createRAGSession } from "../../../api/rag";

const defaultSessionData = {
  name: "",
  description: "",
  documents: [],
  parameters: {
    chunking_model: {
      component: "SimpleChunker",
      params: {
        chunk_size: 500,
        chunk_overlap: 50,
      },
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
  onBack,
  onClose,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [sessionData, setSessionData] = useState({
    ...defaultSessionData,
    name: initialData?.name || "",
    description: initialData?.description || "",
    documents: initialData?.documents || [],
  });
  const [saving, setSaving] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    chunking: true,
    retriever: true,
    generator: true,
    prompt: true,
  });

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

      await createRAGSession(finalSessionData);
      enqueueSnackbar("RAG Session created successfully", { variant: "success" });
      onClose();
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
        gap={2}
        height="100%"
        width="100%"
      >
        {/* Header */}
        <Box>
          <Typography variant="h5" component="h1" sx={{ mb: 1 }}>
            Create RAG Session - Step 2: Configuration
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Configure the components for your RAG session. Click "Open Advanced
            Configuration" for fine-tuned control over each component.
          </Typography>
        </Box>

        {/* Configuration Sections - Scrollable */}
        <Box
          sx={{
            flexGrow: 1,
            overflow: "auto",
            pr: 1,
            "&::-webkit-scrollbar": {
              width: "8px",
            },
            "&::-webkit-scrollbar-track": {
              backgroundColor: "action.hover",
              borderRadius: "4px",
            },
            "&::-webkit-scrollbar-thumb": {
              backgroundColor: "primary.main",
              borderRadius: "4px",
            },
          }}
        >
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
              <AccordionDetails sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
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
              <AccordionDetails sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
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
              <AccordionDetails sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
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
              <AccordionDetails sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <PromptSection
                  promptId={sessionData.parameters.prompt_id}
                  setPromptId={updatePromptId}
                />
              </AccordionDetails>
            </Accordion>
          </Box>
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
            onClick={onBack}
            disabled={saving}
          >
            Back
          </Button>
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
            disabled={saving}
            sx={{ minWidth: 120 }}
          >
            {saving ? <CircularProgress size={20} /> : "Save Session"}
          </Button>
        </Box>
      </Box>
    </CenterBox>
  );
}
