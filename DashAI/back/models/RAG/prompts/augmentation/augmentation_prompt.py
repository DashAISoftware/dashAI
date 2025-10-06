from typing import List, Tuple, Any

from DashAI.back.models.RAG.prompts.prompt import Prompt

class AugmentationPrompt(Prompt):
    """
    AugmentationPrompt class for generating augmented retrieval prompts,
    it uses the language model to generate keywords or phrases that can be used to augment the input.
    """

    required_placeholders = ["{input}", "{history}", "{n_search_terms}"]

    def format(
            self,
            input: str,
            history: List[Tuple[str, str]],
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
        raise NotImplementedError("Subclasses must implement this method.")