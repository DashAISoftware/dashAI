import React, { useEffect, useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import SideBar from "../../threeSectionLayout/panelContainers/SideBar";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { getRAGSession, updateGenerativeSessionParams } from "../../../api/rag";
import PromptParamsCard from "./PromptParamsCard";
import GeneratorParamsCard from "./GeneratorParamsCard";

/**
 * Side panel for viewing and editing RAG session parameters (prompt and generator config).
 *
 * @param {object} props
 * @param {number|string} props.selectedSessionId - The currently selected RAG session ID.
 * @returns {JSX.Element} The params panel with save capability.
 */
export default function RAGParamsPanel({ selectedSessionId }) {
  const { t } = useTranslation(["generative"]);
  const { enqueueSnackbar } = useSnackbar();
  const [promptModel, setPromptModel] = useState({ component: "", params: {} });
  const [generatorModel, setGeneratorModel] = useState({
    component: null,
    params: {},
  });
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
        setPromptModel(params.prompt || { component: "", params: {} });
        setGeneratorModel({
          component: params.generation_model?.component || null,
          params: params.generation_model?.params || {},
        });
        // Store original parameters snapshot
        originalParamsRef.current = {
          prompt: params.prompt || { component: "", params: {} },
          generation_model: {
            component: params.generation_model?.component || null,
            params: params.generation_model?.params || {},
          },
        };
      })
      .catch((err) => {
        console.error("Failed to load RAG session:", err);
        enqueueSnackbar(t("generative:rag.paramsPanel.failedToLoad"), {
          variant: "error",
        });
      })
      .finally(() => setLoading(false));
  }, [selectedSessionId, enqueueSnackbar]);

  /** Whether the current prompt or generator params differ from the last saved snapshot. */
  const hasParamChanges = React.useMemo(() => {
    if (!originalParamsRef.current) return false;
    const original = originalParamsRef.current;
    const hasPromptChanged =
      JSON.stringify(original.prompt) !== JSON.stringify(promptModel);
    const hasComponentChanged =
      original.generation_model.component !== generatorModel.component;
    const hasParamsChanged =
      JSON.stringify(original.generation_model.params) !==
      JSON.stringify(generatorModel.params);
    return hasPromptChanged || hasComponentChanged || hasParamsChanged;
  }, [promptModel, generatorModel, savedVersion]);

  /** Persists the current prompt and generator parameters to the backend. */
  const handleSave = async () => {
    if (!selectedSessionId || !hasParamChanges) return;
    const payload = {
      parameters: {
        prompt: promptModel,
        generation_model: {
          component: generatorModel.component,
          params: generatorModel.params,
        },
      },
    };

    try {
      await updateGenerativeSessionParams(
        selectedSessionId,
        payload.parameters,
      );
      enqueueSnackbar(t("generative:rag.paramsPanel.updated"), {
        variant: "success",
      });
      // Update the snapshot after successful save and trigger recalculation
      originalParamsRef.current = payload.parameters;
      setSavedVersion((v) => v + 1);
    } catch (err) {
      console.error("Failed to update RAG session:", err);
      enqueueSnackbar(t("generative:rag.paramsPanel.failedToUpdate"), {
        variant: "error",
      });
    }
  };

  return (
    <SideBar>
      <Box
        sx={{
          p: 2,
          height: "100%",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        <Typography variant="h6">
          {t("generative:rag.paramsPanel.title")}
        </Typography>

        <Box sx={{ overflow: "auto", flex: 1 }}>
          <Box sx={{ mb: 2 }}>
            <PromptParamsCard
              promptModel={promptModel}
              setPromptModel={setPromptModel}
              onTokenCountChange={() => {}}
            />
          </Box>

          <Box sx={{ mt: 2 }}>
            <GeneratorParamsCard
              generatorModel={generatorModel}
              setGeneratorModel={setGeneratorModel}
              chunkSize={0}
              topK={0}
              promptTokenCount={0}
              setIsValid={setIsValid}
            />
          </Box>
        </Box>

        <Box
          sx={{ display: "flex", gap: 1, justifyContent: "flex-end", pt: 1 }}
        >
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={
              loading || !isValid || !selectedSessionId || !hasParamChanges
            }
          >
            {t("generative:rag.paramsPanel.save")}
          </Button>
        </Box>
      </Box>
    </SideBar>
  );
}
