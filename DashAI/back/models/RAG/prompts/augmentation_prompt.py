from typing import List, Tuple, Any

from DashAI.back.models.RAG.prompts.base_prompt import BasePrompt

class AugmentationPrompt(BasePrompt):
    """
    AugmentationPrompt class for generating augmented retrieval prompts,
    it uses the language model to generate keywords or phrases that can be used to augment the input.
    """
    @staticmethod
    def format(
            input: str, 
            history:List[Tuple[str, str]],
            n_seach_terms: int = 5,
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
        if history:
            formatted_history = "\n".join(
                [f"Q: {h_input}\nA: {h_output}" for h_input, h_output in history]
            )
        else:
            formatted_history = ""

        keyword_dict = "{'keywords': [" 
        for i in range(n_seach_terms):
            keyword_dict += f"'keyword_{i+1}', "
        keyword_dict = keyword_dict[:-2] + "]}"
        return f"""
        You are a intelligent and insightful assistant. Your task is to generate keywords or phrases to search for
        relevant information based on the input provided. The keywords or phrases should be relevant to the input
        and should help in retrieving useful information to improve the precision of the response.
        The user input is:
        {input}
        The chat history is: 
        {formatted_history}
        The number of keywords or phrases to generate is {n_seach_terms}.
        Please generate {n_seach_terms} keywords or phrases that can be used to search for relevant information.
        The keywords or phrases should be concise and to the point. You must fill the following template:
        {keyword_dict}
        """
    