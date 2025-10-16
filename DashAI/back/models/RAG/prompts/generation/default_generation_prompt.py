from typing import Any, List, Tuple
from DashAI.back.models.RAG.prompts.generation.generation_prompt import GenerationPrompt

template = """
You are a intelligent and insightful assistant. 
Your task is to generate a response to the user message. To do this, you will be provided with the user input,
documents retrieved from a database that can be useful for the response, and the chat history.
The user input is:
{input}
The retrieved documents are:
{chunks}
The chat history is:
{history}
Please generate a response that takes into account the input, the retrieved documents and the chat history, you
must respond in a conversational manner. 
Use the information from the retrieved documents to provide a more accurate and relevant response to the user,
if the information is not relevant to the user input, you can ignore it.
Your response should be clear, concise and relevant to the input provided, using natural language.
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
        super().__init__(**kwargs)

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