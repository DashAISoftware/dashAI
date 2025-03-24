from typing import Any
from llama_cpp import Llama

from DashAI.back.models.llm_generation_model import LLMGenerationModel


class GemmaModel(LLMGenerationModel):
    """Llama model for text generation using llama.cpp library."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_id = "ggml-org/gemma-1.1-7b-it-Q4_K_M-GGUF"
        self.filename = "*.gguf"

        self.model = Llama.from_pretrained(
            repo_id=self.model_id, filename=self.filename, verbose=True
        )

    def generate(self, prompt: str) -> str:
        """Generate text based on prompts."""
        output = self.model(
            f"Q: {prompt} A:", max_tokens=self.max_tokens, stop=["\n", "Q:"], echo=True
        )
        return output["choices"][0]["text"]
    
    def __call__(self, prompt: str) -> str:
        return self.generate(prompt)