from typing import Any, List, Tuple
from DashAI.back.models.RAG.prompts.prompt import Prompt

class ContextMergePrompt(Prompt):
    """
    ContextMergePrompt class for generating prompts that merge the use input, the retrieved 
    documents and the chat history into a single context for the language model.
    """
    required_placeholders = ["{input}", "{history}", "{chunks}"]

    @staticmethod
    def format(
            input: str,
            history: List[Tuple[str, str]],
            chunks: List[str],
            **kwargs: Any
        ) -> str:
        raise NotImplementedError("Subclasses must implement this method.")