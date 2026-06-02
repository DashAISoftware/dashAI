import json
from typing import Any, List, Optional, Tuple

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import ProcessData
from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class RAGTask(BaseGenerativeTask):
    """Class for RAG Task.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs": {"str": {"min": 1, "max": 1}},
        "outputs": {"str": {"min": 1, "max": 1}, "Dict": {"min": 1, "max": 1}},
    }

    DISPLAY_NAME: str = MultilingualString(
        en="RAG Task",
        es="Tarea RAG",
    )
    DESCRIPTION: str = MultilingualString(
        en="""
        This task generates a text response with an LLM model based on documents provided.
        """,
        es="""
        Esta tarea genera una respuesta de texto con un modelo LLM basado en los documentos proporcionados.
        """,
    )

    USE_HISTORY: bool = True

    def prepare_for_task(
        self,
        input: List[ProcessData],
        history: Optional[List[Tuple[str, str]]] = None,
    ) -> list[dict[str, str]]:
        """Prepare the input by including the history.

        Parameters
        ----------
        input : str
            The current input to be processed.
            E.g.:
            ["Tell me a joke."]

        history : Optional[List[Tuple[str, str]]], optional
            The history of previous inputs and outputs, by default None. E.g.:
            [("Hello!", "Hello! How can I assist you today?")]

        Returns
        -------
        str
            The input prepared with the history to be used by the model.
            E.g.:
                [{"role": "user", "content": "Hello!"},
                 {"role": "assistant", "content": "Hello! How can I assist you today?"},
                 {"role": "user", "content": "Tell me a joke."}]
        """
        input = str(input[0].data)

        prepared_input = [{"role": "user", "content": input}]

        if not history:
            return prepared_input

        context = [
            (
                {"role": "user", "content": h_input},
                {"role": "assistant", "content": h_output},
            )
            for (h_input, h_output) in history
        ]
        context = [entry for input_output in context for entry in input_output]
        prepared_input = context + prepared_input
        return prepared_input

    def prepare_input_for_database(
        self,
        input: List[str],
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Prepare the input for the database.

        Parameters
        ----------
        input : str
            The input to be prepared.

        Returns
        -------
        List[Tuple[str, str]]
            Input with the new types as a list of tuples containing the data
            and its type

        """
        return [(input[0], "str")]

    def process_output(
        self,
        output: List[Any],
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Process the output of a generative model.

        file_name (Str): Indicates the name of the file.
        path (Str): Indicates the path where the output will be stored.
        """
        message, chunks = output
        return [(str(message), "str"), (json.dumps(chunks, ensure_ascii=False, default=str), "Dict")]

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
