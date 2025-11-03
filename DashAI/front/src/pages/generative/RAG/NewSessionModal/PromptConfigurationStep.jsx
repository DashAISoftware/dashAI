import { useEffect, useState } from "react";
import PromptSelectionTable from "../../../../components/generative/RAG/PromptSelectionTable";
import { getRAGPrompts } from "../../../../api/rag";

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
    <PromptSelectionTable
      prompts={prompts}
      loading={loading}
      rowSelectionModel={selectedPromptId}
      onRowSelectionModelChange={setSelectedPromptId}
      setSessionData={setSessionData}
    />
  );
}
