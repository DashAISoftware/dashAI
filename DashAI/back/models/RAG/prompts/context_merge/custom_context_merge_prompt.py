from typing import Any, List, Tuple
from DashAI.back.models.RAG.prompts.context_merge.context_merge_prompt import ContextMergePrompt

class CustomContextMergePrompt(ContextMergePrompt):
    """
    ContextMergePrompt class for generating prompts that merge the use input, the retrieved 
    documents and the chat history into a single context for the language model.
    """
    required_placeholders = ["{input}", "{documents}", "{history}"]
    

    def __init__(self, template: str):
        if not self.validate_template(template):
            raise ValueError("The template is missing required placeholders.")
        self.template = template

    def format(
            self,
            input: str,
            history: List[Tuple[str, str]],
            chunks: List[str],
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
                [f"User message: {h_input}\n Response: {h_output}" for h_input, h_output in history]
            ))
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{documents}", "\n".join(chunks))
        return buffer
