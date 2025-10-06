from typing import List, Tuple, Any

from DashAI.back.models.RAG.prompts.prompt import Prompt

class CustomAugmentationPrompt(Prompt):
    """
    User-defined augmentation prompt template for generating augmented retrieval prompts.
    It uses the language model to generate keywords or phrases that can be used to augment the input
    """


    def __init__(self, template: str):
        if not self.validate_template(template):
            raise ValueError("The template is missing required placeholders.")
        self.template = template


    def format(
            self,
            input: str, 
            history:List[Tuple[str, str]],
            n_search_terms: int = 5,
            **kwargs: Any
        ) -> str:
        """
        Instantiate and format the prompt for augmentation.
        Args:
            input (str): The input to be formatted.
            history (List[Tuple[str, str]]): The history of the conversation.
            n_seach_terms (int): The number of search terms to generate.
            **kwargs: Additional keyword arguments for formatting.
        Returns:
            str: The formatted prompt.
        """
        buffer = self.template
        if history:
            buffer = buffer.replace("{history}", "\n".join(
                [f"Q: {h_input}\nA: {h_output}" for h_input, h_output in history]
            ))
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{n_search_terms}", str(n_search_terms))
        return buffer