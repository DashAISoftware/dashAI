from DashAI.back.models.RAG.prompts.generation.generation_prompt import GenerationPrompt
from typing import Any, List, Tuple
template = """
You are an intelligent and insightful assistant. Your task is to provide a concise and accurate answer to the user's question based on the provided context.
The user question is:
{input}
The context documents are:
{chunks}
The chat history is:
{history}
Please generate a clear, concise, and relevant answer to the user's question using the information from the context documents. If the context does not provide enough information, respond with "I don't know".
Avoid including any information not present in the context documents.
Your answer should be in natural language and directly address the user's question.
"""


class DefaultQnAGenerationPrompt(GenerationPrompt):
    """
    Default generation prompt for Question Answering tasks.
    This prompt is designed to guide the language model in generating answers based on provided context chunks.
    """

    metadata = {
        "name": "Default QnA Generation Prompt",
        "description": "Default prompt template used in the language generation step of RAG for Question Answering tasks.",
        "type": "generation",
        "required_placeholders": GenerationPrompt.required_placeholders,
        "optional_placeholders": GenerationPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The user input message.",
            "{chunks}": "The document chunks to be included in the context."
        },
        "template": template
    }
    template = template

    def __init__(self, **kwargs):
        self.template = kwargs.pop("template")


    @staticmethod
    def format(
            input: str, 
            chunks: List[str],
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
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{chunks}", chunks)
        return buffer