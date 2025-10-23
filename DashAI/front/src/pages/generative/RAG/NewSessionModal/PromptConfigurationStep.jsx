import { useEffect, useState } from "react";
import PromptSelectionTable from "../../../../components/generative/RAG/PromptSelectionTable";
import { getRAGPrompts } from "../../../../api/rag";

export default function PromptConfigurationStep({ setNextEnabled }) {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setNextEnabled && setNextEnabled(true);
    getRAGPrompts()
      .then((data) => setPrompts(data))
      .catch(() => setPrompts([]))
      .finally(() => setLoading(false));
  }, []);

  return <PromptSelectionTable prompts={prompts} loading={loading} />;
}
