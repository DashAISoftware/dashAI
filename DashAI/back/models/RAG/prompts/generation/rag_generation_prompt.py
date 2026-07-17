from typing import Any, Tuple

from DashAI.back.models.RAG.prompts.prompt import Prompt


class RAGGenerationPrompt(Prompt):
    """
    RAGGenerationPrompt class for formatting prompts used in the language
    generation step of RAG.
    """

    required_placeholders = ["{input}", "{chunks}"]
    optional_placeholders = []

    @staticmethod
    def format(
        input: str,
        chunks: str,
        history: Tuple[Tuple[str, str], ...] | None = None,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError("Subclasses must implement this method.")
