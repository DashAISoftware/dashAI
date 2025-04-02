from typing import Any

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

    def prepare_for_task(self, input: str) -> str:
        """Change the inputs to suit the image generation task.

        Parameters
        ----------
        inputs : str
            Input to be changed

        Returns
        -------
        str
            Input with the new types
        """
        return input

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
