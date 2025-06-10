from typing import Any, List

from DashAI.back.dependencies.database.models import ProcessData
from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class TextToTextGenerationTask(BaseGenerativeTask):
    """Base class for image generation tasks.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [str],
        "outputs_types": [str],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DESCRIPTION: str = (
        "This task uses a large language model (LLM) "
        "to generate text from a given prompt."
    )

    USE_HISTORY: bool = True

    def prepare_for_task(
        self,
        input: List[ProcessData],
        **kwargs: Any,
    ) -> str:
        """Prepare the input by including the history in Q: A: format.

        Parameters
        ----------
        input : str
            The current input to be processed.

        Returns
        -------
        str
            The input prepared with the history in Q: A: format.
        """
        input = str(input[0].data)
        history = kwargs.get("history", None)  # type: Optional[List[Tuple[str, str]]]
        if not history:
            return f"Q: {input}\nA:"

        history = [(input[0], output[0]) for (input, output) in history]
        context = "\n".join(
            [f"Q: {h_input}\nA: {h_output}" for h_input, h_output in history]
        )

        prepared_input = f"{context}\nQ: {input}\nA:"
        print(prepared_input)
        return prepared_input

    def prepare_input_for_database(
        self,
        input: List[str],
        **kwargs: Any,
    ) -> List[tuple[str, str]]:
        """Prepare the input for the database.

        Parameters
        ----------
        input : str
            The input to be prepared.

        Returns
        -------
        List[tuple[str, str]]
            Input with the new types as a list of tuples containing the data
            and its type

        """
        return [(input[0], "str")]

    def process_output(
        self,
        output: List[Any],
        **kwargs: Any,
    ) -> List[tuple[str, str]]:
        """Process the output of a generative model.

        file_name (Str): Indicates the name of the file.
        path (Str): Indicates the path where the output will be stored.
        """

        return [(str(output[0]), "str")]

    def process_output_from_database(
        self,
        output: List[ProcessData],
        **kwargs: Any,
    ) -> List[ProcessData]:
        """Process the output from the database.

        Parameters
        ----------
        output : list[str]
            The output data to be processed.

        Returns
        -------
        list[str]
            The processed output data.
        """

        return output

    def process_input_from_database(
        self,
        input: List[ProcessData],
        **kwargs: Any,
    ) -> List[ProcessData]:
        """Process the input from the database.

        Parameters
        ----------
        input : list[str]
            The input data to be processed.

        Returns
        -------
        list[str]
            The processed input data.
        """
        return input
