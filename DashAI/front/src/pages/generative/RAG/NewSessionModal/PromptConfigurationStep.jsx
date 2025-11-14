import { useEffect, useState } from "react";
import PromptSelectionTable from "../../../../components/generative/RAG/PromptSelectionTable";
import { getRAGPrompts } from "../../../../api/rag";
import { Stack } from "@mui/system";
import { Typography } from "@mui/material";

export default function PromptConfigurationStep({
  setNextEnabled,
  sessionData,
  setSessionData,
}) {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPromptId, setSelectedPromptId] = useState([]);

  useEffect(() => {
    getRAGPrompts()
      .then((data) => setPrompts(data))
      .catch(() => setPrompts([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setNextEnabled(selectedPromptId.length > 0);
    if (selectedPromptId.length > 0) {
      const prompt = prompts.find((p) => p.id === selectedPromptId[0]);
      if (prompt) {
        setSessionData((prev) => ({
          ...prev,
          parameters: {
            ...prev.parameters,
            prompt_id: prompt.id,
          },
        }));
      }
    }
  }, [selectedPromptId, prompts]);


  return (
    <Stack spacing={2}>
      <Typography variant="h6">Select a Prompt Template or create a new one</Typography>
      <Typography variant="body2">Prompt templates define how the chunks (pieces of documents) and chat messages are integrated to generate responses. You can select an existing prompt template or create a new one to customize the behavior of your RAG session.</Typography>
      <PromptSelectionTable
        prompts={prompts}
        loading={loading}
        rowSelectionModel={selectedPromptId}
        onRowSelectionModelChange={setSelectedPromptId}
        setSessionData={setSessionData}
        showTableTitle={true}
      />
    </Stack>
  );
}
