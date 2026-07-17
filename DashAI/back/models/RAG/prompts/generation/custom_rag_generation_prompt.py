from typing import Any

from DashAI.back.models.RAG.prompts.generation.rag_generation_prompt import (
    RAGGenerationPrompt,
)


class CustomRAGGenerationPrompt(RAGGenerationPrompt):
    """
    CustomRAGGenerationPrompt class for user-defined prompt templates
    used in the language generation step of RAG.
    """

    metadata = {
        "name": "Custom RAG Generation Prompt",
        "description": "User-defined prompt template used in the language"
        " generation step of RAG.",
        "type": "generation",
        "required_placeholders": RAGGenerationPrompt.required_placeholders,
        "optional_placeholders": RAGGenerationPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The user input message.",
            "{chunks}": "The document chunks to be included in the context.",
        },
    }

    def __init__(self, **kwargs: Any):
        self.template = kwargs.pop("template")

    def format(self, input: str, chunks: str, **kwargs: Any) -> str:
        """
        Format the prompt using the provided template.

        Args:
            input (str): The user input message.
            history (List[Tuple[str, str]]): The chat history to be
                included in the context.
            chunks (List[str]): The document chunks to be included in the
                context.
            **kwargs: Additional keyword arguments for formatting.

        Returns:
            str: The formatted prompt.
        """
        buffer = self.template
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{chunks}", chunks)
        return buffer
