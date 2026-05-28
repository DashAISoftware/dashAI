from typing import Any, List, Tuple

from DashAI.back.models.RAG.prompts.augmentation import AugmentationPrompt


class CustomAugmentationPrompt(AugmentationPrompt):
    """
    User-defined augmentation prompt template for generating augmented retrieval prompts.
    It uses the language model to generate keywords or phrases that can be used to augment the input
    """

    metadata = {
        "name": "Custom Augmentation Prompt",
        "description": "User-defined prompt template for generating augmented retrieval prompts.",
        "type": "augmentation",
        "required_placeholders": AugmentationPrompt.required_placeholders,
        "optional_placeholders": AugmentationPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The user input message.",
            "{n_search_terms}": "The number of search terms to generate.",
        },
    }

    required_placeholders = ["{input}", "{n_search_terms}"]
    optional_placeholders = []

    def __init__(self, **kwargs):
        self.template = kwargs.pop("template")

    def format(
        self,
        input: str,
        n_search_terms: int,
        history: List[Tuple[str, str]] = None,
        **kwargs: Any,
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
            buffer = buffer.replace(
                "{history}",
                "\n".join(
                    [f"Q: {h_input}\nA: {h_output}" for h_input, h_output in history]
                ),
            )
        buffer = buffer.replace("{input}", input)
        buffer = buffer.replace("{n_search_terms}", str(n_search_terms))
        return buffer
