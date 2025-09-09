from typing import Any

from DashAI.back.models.base_model import BaseModel

class Prompt(BaseModel):
    """
    Base class for all RAG prompt templates.
    This class defines the interface for creating and formatting prompts.
    """
    @staticmethod
    def format(input: str, **kwargs: Any) -> str:
        """
        Instantiate and format the prompt.
        Args:
            input (str): The input to be formatted.
            **kwargs: Additional keyword arguments for formatting.
        Returns:
            str: The formatted prompt.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    