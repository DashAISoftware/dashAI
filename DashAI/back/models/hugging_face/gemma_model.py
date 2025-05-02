from typing import List

from llama_cpp import Llama

from DashAI.back.models.llm_generation_model import LLMGenerationModel


class GemmaModel(LLMGenerationModel):
    """Llama model for text generation using llama.cpp library."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_id = "ggml-org/gemma-1.1-7b-it-Q4_K_M-GGUF"
        self.filename = "*.gguf"

        self.model = Llama.from_pretrained(
            repo_id=self.model_id, filename=self.filename, verbose=True, n_ctx=self.n_ctx,
        )

    # def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
    def generate(self, prompt: str) -> List[str]:
        """Generate text based on prompts."""
        full_prompt = f"Q: {prompt} A:"
        if len(full_prompt) > self.model.n_ctx:
            full_prompt = full_prompt[-self.model.n_ctx:]

        output = self.model(
            full_prompt, max_tokens=self.max_tokens, temperature=self.temperature, frequency_penalty=self.frequency_penalty, stop=["Q:"], echo=False
        )
        generated_text = output["choices"][0]["text"]
        clean_text = generated_text.replace(f"Q: {prompt} A:", "").strip()
        return [clean_text]

    def __call__(self, prompt: str) -> List[str]:
        return self.generate(prompt)
