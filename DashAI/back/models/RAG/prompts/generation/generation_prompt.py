from typing import Any, List, Tuple
from DashAI.back.models.RAG.prompts.prompt import Prompt

class GenerationPrompt(Prompt):
    """
    GenerationPrompt class for formatting prompts used in the language generation step of RAG.
    """
    required_placeholders = ["{input}", "{chunks}"]
    optional_placeholders = ["{history}"]

    @staticmethod
    def format(
            input: str,
            chunks: List[str],
            history: List[Tuple[str, str]] = [],
            **kwargs: Any
        ) -> str:
        raise NotImplementedError("Subclasses must implement this method.")