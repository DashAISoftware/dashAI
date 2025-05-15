from typing import Any, List, Tuple
from DashAI.back.models.RAG.prompts.base_prompt import BasePrompt

class ContextMergePrompt(BasePrompt):
    """
    ContextMergePrompt class for generating prompts that merge the use input, the retrieved 
    documents and the chat history into a single context for the language model.
    """
    @staticmethod
    def format(
            input: str, 
            history:List[Tuple[str, str]],
            documents: str,
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
        return f"""
        You are a intelligent and insightful assistant. 
        Your task is to generate a response to the user message. To do this, you will be provided with the user input,
        documents retrieved from a database that can be useful for the response, and the chat history.
        The user input is:
        {input}
        The retrieved documents are:
        {documents}
        The chat history is:
        {history}
        Please generate a response that takes into account the input, the retrieved documents and the chat history, you
        must respond in a conversational manner. 
        Use the information from the retrieved documents to provide a more accurate and relevant response to the user,
        if the information is not relevant to the user input, you can ignore it.
        Your response should be clear, concise and relevant to the input provided, using natural language.

        RESPONSE:
        """