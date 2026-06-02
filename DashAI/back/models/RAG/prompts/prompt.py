from typing import Any, Dict, List

from DashAI.back.core.schema_fields import BaseSchema, schema_field, string_field
from DashAI.back.models.base_model import BaseModel


class PromptSchema(BaseSchema):
    template: str = schema_field(
        string_field(),
        placeholder="",
        description="The prompt template with placeholders.",
    )


class Prompt(BaseModel):
    """
    Base class for all RAG prompt templates.
    This class defines the interface for creating and formatting prompts.
    """

    SCHEMA = PromptSchema
    DESCRIPTION: str = "Base class for RAG prompts."
    DISPLAY_NAME: str = "Base RAG Prompt"
    id: int
    name: str
    REQUIRED_EXTRA_KWARGS = []

    def load(self, **kwargs: Any) -> None:
        pass

    def save(self) -> None:
        pass

    def train(self, **kwargs: Any) -> None:
        pass

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        metadata = cls.metadata if hasattr(cls, "metadata") else {}
        return metadata

    @classmethod
    def get_required_placeholders(cls) -> List[str]:
        """
        Get the list of required placeholders for the prompt template.
        Returns:
            List[str]: List of required placeholders.
        """
        assert hasattr(cls, "required_placeholders"), (
            "Subclasses must define 'required_placeholders' class attribute."
        )
        return cls.required_placeholders

    def get_optional_placeholders(self) -> List[str]:
        """
        Get the list of optional placeholders for the prompt template.
        Returns:
            List[str]: List of optional placeholders.
        """
        assert hasattr(self, "optional_placeholders"), (
            "Subclasses must define 'optional_placeholders' class attribute."
        )
        return self.optional_placeholders

    @classmethod
    def validate_template(cls, template: str) -> bool:
        """
        Validate that the template contains all required placeholders.
        Args:
            template (str): The prompt template to be validated.
        Returns:
            bool: True if the template is valid, False otherwise.
        """
        return all(placeholder in template for placeholder in cls.required_placeholders)

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
