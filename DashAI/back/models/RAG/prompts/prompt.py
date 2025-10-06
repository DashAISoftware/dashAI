from typing import Any, List

from DashAI.back.models.base_model import BaseModel

class Prompt(BaseModel):
    """
    Base class for all RAG prompt templates.
    This class defines the interface for creating and formatting prompts.
    """


    @classmethod
    def get_required_placeholders(cls) -> List[str]:
        """
        Get the list of required placeholders for the prompt template.
        Returns:
            List[str]: List of required placeholders.
        """
        return cls.required_placeholders


    @classmethod
    def validate_template(cls, template: str) -> bool:
        """
        Validate that the template contains all required placeholders.
        Args:
            template (str): The prompt template to be validated.
        Returns:
            bool: True if the template is valid, False otherwise.
        """
        for placeholder in cls.required_placeholders:
            if placeholder not in template:
                return False
        return True
   

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
    