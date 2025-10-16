from typing import Any, Dict, List

from DashAI.back.models.base_model import BaseModel
from DashAI.back.core.schema_fields import BaseSchema, schema_field, string_field
from DashAI.back.dependencies.database.models import (
    RAGPrompt as PromptDBModel)

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
    REQUIRED_EXTRA_KWARGS = ["db"]
    id: int

    def __init__(self, **kwargs):
        self.db = kwargs.pop("db")
        kwargs = self.validate_and_transform(kwargs)
        self.template = kwargs.get("template")
        assert self.validate_template(self.template), "The template is missing required placeholders."
        self.class_name = self.__class__.__name__
        self.params = kwargs

        stored_model = self.db.query(PromptDBModel).filter_by(
            class_name = self.class_name,
            parameters = self.params
        ).first()
        if stored_model:
            self.id = stored_model.id
        else:
            new_model = PromptDBModel(
                class_name=self.class_name,
                parameters=self.params
            )
            self.db.add(new_model)
            self.db.commit()
            self.id = new_model.id


        
    def load(self, **kwargs: Any) -> None:
        pass

    def save(self) -> None:
        pass

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        if hasattr(cls, 'metadata'):
            metadata = cls.metadata
        else:
            metadata = {}
        return metadata

        

    @classmethod
    def get_required_placeholders(cls) -> List[str]:
        """
        Get the list of required placeholders for the prompt template.
        Returns:
            List[str]: List of required placeholders.
        """
        assert hasattr(cls, 'required_placeholders'), "Subclasses must define 'required_placeholders' class attribute."
        return cls.required_placeholders
    
    def get_optional_placeholders(self) -> List[str]:
        """
        Get the list of optional placeholders for the prompt template.
        Returns:
            List[str]: List of optional placeholders.
        """
        assert hasattr(self, 'optional_placeholders'), "Subclasses must define 'optional_placeholders' class attribute."
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
    