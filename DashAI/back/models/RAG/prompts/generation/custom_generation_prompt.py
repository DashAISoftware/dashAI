from typing import Any, List, Tuple
from DashAI.back.models.RAG.prompts.generation.generation_prompt import GenerationPrompt

class CustomGenerationPrompt(GenerationPrompt):
    """
    CustomGenerationPrompt class for user-defined prompt templates used in the language generation step of RAG.
    """

    metadata = {
        "name": "Custom Generation Prompt",
        "description": "User-defined prompt template used in the language generation step of RAG.",
        "type": "generation",
        "required_placeholders": GenerationPrompt.required_placeholders,
        "optional_placeholders": GenerationPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The user input message.",
            "{history}": "The chat history (optional) to be included in the context.",
            "{documents}": "The document chunks to be included in the context."
        }
    }
    

    def __init__(self, template: str):
        if not self.validate_template(template):
            raise ValueError("The template is missing required placeholders.")
        self.template = template

    def format(
            self,
            input: str,
            chunks: List[str],
            history: List[Tuple[str, str]] = [],
            **kwargs: Any
        ) -> str:
        """
        Format the prompt using the provided template.

        Args:
            input (str): The user input message.
            history (List[Tuple[str, str]]): The chat history to be included in the context.
            chunks (List[str]): The document chunks to be included in the context.
            **kwargs: Additional keyword arguments for formatting.
        
        Returns:
            str: The formatted prompt.
        """
        buffer = self.template
        if history:
            buffer = buffer.replace("{history}", "\n".join(
                [f"User message: {h_input}\nResponse: {h_output}" for h_input, h_output in history]
            ))
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{documents}", "\n".join(chunks))
        return buffer
