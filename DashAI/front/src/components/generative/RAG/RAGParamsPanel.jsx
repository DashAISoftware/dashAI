import React, { useEffect, useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import SideBar from "../../threeSectionLayout/panelContainers/SideBar";
import { useSnackbar } from "notistack";
import {
  getRAGSession,
  updateGenerativeSessionParams,
} from "../../../api/rag";
import PromptSection from "../../../pages/generative/simplified-RAG/sections/PromptSection";
import GeneratorSection from "../../../pages/generative/simplified-RAG/sections/GeneratorSection";

export default function RAGParamsPanel({ selectedSessionId }) {
  const { enqueueSnackbar } = useSnackbar();
  const [promptId, setPromptId] = useState(null);
  const [generatorModel, setGeneratorModel] = useState({ component: null, params: {} });
  const [loading, setLoading] = useState(false);
  const [isValid, setIsValid] = useState(true);
  const [savedVersion, setSavedVersion] = useState(0);
  const originalParamsRef = React.useRef(null);

  useEffect(() => {
    if (!selectedSessionId) return;
    setLoading(true);
    getRAGSession(selectedSessionId)
      .then((session) => {
        const params = session.parameters || {};
        setPromptId(params.prompt_id || null);
        setGeneratorModel({
          component: params.generation_model?.component || null,
          params: params.generation_model?.params || {},
        });
        // Store original parameters snapshot
        originalParamsRef.current = {
          prompt_id: params.prompt_id || null,
          generation_model: {
            component: params.generation_model?.component || null,
            params: params.generation_model?.params || {},
          },
        };
      })
      .catch((err) => {
        console.error("Failed to load RAG session:", err);
        enqueueSnackbar("Failed to load RAG session", { variant: "error" });
      })
      .finally(() => setLoading(false));
  }, [selectedSessionId, enqueueSnackbar]);

  // Detect if parameters have changed
  const hasParamChanges = React.useMemo(() => {
    if (!originalParamsRef.current) return false;
    const original = originalParamsRef.current;
    const hasPromptIdChanged = original.prompt_id !== promptId;
    const hasComponentChanged = original.generation_model.component !== generatorModel.component;
    const hasParamsChanged = JSON.stringify(original.generation_model.params) !== JSON.stringify(generatorModel.params);
    return hasPromptIdChanged || hasComponentChanged || hasParamsChanged;
  }, [promptId, generatorModel, savedVersion]);

  const handleSave = async () => {
    if (!selectedSessionId || !hasParamChanges) return;
    const payload = {
      parameters: {
        prompt_id: promptId,
        generation_model: {
          component: generatorModel.component,
          params: generatorModel.params,
        },
      },
    };

    try {
      await updateGenerativeSessionParams(selectedSessionId, payload.parameters);
      enqueueSnackbar("RAG parameters updated", { variant: "success" });
      // Update the snapshot after successful save and trigger recalculation
      originalParamsRef.current = payload.parameters;
      setSavedVersion((v) => v + 1);
    } catch (err) {
      console.error("Failed to update RAG session:", err);
      enqueueSnackbar("Failed to update RAG parameters", { variant: "error" });
    }
  };

  return (
    <SideBar>
      <Box sx={{ p: 2, height: "100%", display: "flex", flexDirection: "column", gap: 2 }}>
        <Typography variant="h6">RAG Parameters</Typography>

        <Box sx={{ overflow: "auto", flex: 1 }}>
          <Box sx={{ mb: 2 }}>
            <PromptSection promptId={promptId} setPromptId={setPromptId} onTokenCountChange={() => {}} />
          </Box>

          <Box sx={{ mt: 2 }}>
            <GeneratorSection
              generatorModel={generatorModel}
              setGeneratorModel={setGeneratorModel}
              chunkSize={0}
              topK={0}
              promptTokenCount={0}
              setIsValid={setIsValid}
            />
          </Box>
        </Box>

        <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end", pt: 1 }}>
          <Button 
            variant="contained" 
            onClick={handleSave} 
            disabled={loading || !isValid || !selectedSessionId || !hasParamChanges}
          >
            Save
          </Button>
        </Box>
      </Box>
    </SideBar>
  );
}
