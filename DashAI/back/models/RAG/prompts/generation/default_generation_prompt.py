from typing import Any, List, Tuple
from DashAI.back.models.RAG.prompts.generation.generation_prompt import GenerationPrompt

template = """
Answer to this question
{input}
Using the following documents as context:
{chunks}
The chat history is:
{history}
"""

class DefaultGenerationPrompt(GenerationPrompt):
    """
    Default prompt template used in the language generation step of RAG.
    """

    metadata = {
        "name": "Default Generation Prompt",
        "description": "Default prompt template used in the language generation step of RAG.",
        "type": "generation",
        "required_placeholders": GenerationPrompt.required_placeholders,
        "optional_placeholders": GenerationPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The user input message.",
            "{history}": "The chat history (optional) to be included in the context.",
            "{chunks}": "The document chunks to be included in the context."
        },
        "template": template
    }

    def __init__(self, **kwargs):
        self.template = kwargs.pop("template")


    @staticmethod
    def format(
            input: str, 
            history:List[Tuple[str, str]],
            chunks: str,
            **kwargs: Any
        ) -> str:
        """
        Instantiate and format the prompt for context merging.
        Args:
            input (str): The input to be formatted.
            documents (str): The retrieved documents to be included in the context.
            history (str): The chat history to be included in the context.
            **kwargs: Additional keyword arguments for formatting.
        Returns:
            str: The formatted prompt.
        """
        buffer = template
        if history:
            buffer = buffer.replace("{history}", "\n".join(
                [f"User message: {h_input}\nResponse: {h_output}" for h_input, h_output in history]
            ))
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{chunks}", chunks)
        return buffer