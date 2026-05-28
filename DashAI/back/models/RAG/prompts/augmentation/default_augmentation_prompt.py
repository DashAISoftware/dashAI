from typing import Any, List, Tuple

from DashAI.back.models.RAG.prompts.augmentation.augmentation_prompt import (
    AugmentationPrompt,
)

template = """
You are a intelligent and insightful assistant. Your task is to generate keywords or phrases to search for
relevant information based on the input provided. The keywords or phrases should be relevant to the input
and should help in retrieving useful information to improve the precision of the response.
The user input is:
{input}
The chat history is: 
{history}
The number of keywords or phrases to generate is {n_search_terms}.
Please generate {n_search_terms} keywords or phrases that can be used to search for relevant information.
The keywords or phrases should be concise and to the point. You must fill the following template:
{
'keywords': ['keyword_1', 'keyword_2', ..., 'keyword_n']}
}
"""


class DefaultAugmentationPrompt(AugmentationPrompt):
    """
    AugmentationPrompt class for generating augmented retrieval prompts,
    it uses the language model to generate keywords or phrases that can be used to augment the input.
    """

    metadata = {
        "name": "Default Augmentation Prompt",
        "description": "Default prompt template for generating augmented retrieval prompts.",
        "type": "augmentation",
        "required_placeholders": AugmentationPrompt.required_placeholders,
        "optional_placeholders": AugmentationPrompt.optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The user input message.",
            "{history}": "The chat history (optional) to be included in the context.",
            "{n_search_terms}": "The number of search terms to generate.",
        },
        "template": template,
    }

    template = template
    required_placeholders = ["{input}", "{n_search_terms}"]
    optional_placeholders = []

    @staticmethod
    def format(
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
        buffer = template
        buffer = buffer.replace("{input}", input)
        if history:
            buffer = buffer.replace(
                "{history}",
                "\n".join(
                    [f"Q: {h_input}\nA: {h_output}" for h_input, h_output in history]
                ),
            )
        else:
            buffer = buffer.replace("{history}", "No previous conversation.")
        buffer = buffer.replace("{n_search_terms}", str(n_search_terms))
        return buffer
