from typing import Any, List, Tuple

from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class LLMGenerationTask(BaseGenerativeTask):
    """Base class for image generation tasks.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [str],
        "outputs_types": [str],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DESCRIPTION: str = "This task generates text from a given prompt."

    DISPLAY_NAME: str = "Text to Text"

    USE_HISTORY: bool = True

    def prepare_for_task(self, input: str, history: List[Tuple[str, str]]) -> str:
        """Prepare the input by including the history in Q: A: format.

        Parameters
        ----------
        input : str
            The current input to be processed.
        history : list[tuple[str, str]]
            A list of tuples where each tuple contains a previous input and its corresponding output.

        Returns
        -------
        str
            The input prepared with the history in Q: A: format.
        """
        context = "\n".join([f"Q: {h_input}\nA: {h_output}" for h_input, h_output in history])

        prepared_input = f"{context}\nQ: {input}\nA:"

        return prepared_input

    def process_output(
        self,
        output: Any,
        *args: Any,
    ) -> str:
        """Process the output of a generative model.

        file_name (Str): Indicates the name of the file.
        path (Str): Indicates the path where the output will be stored.
        """

        return output
