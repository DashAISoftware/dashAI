from typing import List

from llama_cpp import Llama

from DashAI.back.models.llm_generation_model import LLMGenerationModel


class QwenModel(LLMGenerationModel):
    """Llama model for text generation using llama.cpp library."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_id = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
        self.filename = "*q8_0.gguf"

        self.model = Llama.from_pretrained(
            repo_id=self.model_id, filename=self.filename, verbose=True, n_ctx=self.n_ctx
        )

    def generate(self, prompt: str) -> List[str]:

        if len(prompt) > self.model.n_ctx():
            prompt = prompt[-self.model.n_ctx():]

        """Generate text based on prompts."""

        output = self.model(
            prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            stop=["Q:"],
            echo=False,
        )

        generated_text = output["choices"][0]["text"]
        clean_text = generated_text.replace(prompt, "").strip()
        return [clean_text]
