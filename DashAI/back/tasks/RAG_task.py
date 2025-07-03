from typing import Any, List, Tuple
from itertools import chain

from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class RAGTask(BaseGenerativeTask):
    """Class for RAG Task.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [str],
        "outputs_types": [str],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DISPLAY_NAME: str = "Retreival-Augmented Generation (RAG) Task"
    DESCRIPTION: str = "This task generates a text response based on documents provided and chat."

    USE_HISTORY: bool = True

    def prepare_for_task(
        self,
        input: List[str],
        **kwargs: Any,
    ) -> Tuple[str, List[str]]:
        """Prepare the input by including the history in Q: A: format and retrieving the documents.

        Parameters
        ----------
        input : str
            The current input to be processed.
        

        Returns
        -------
        str
            The input message

        list[str]
            The history of the conversation
        """
        
        return input[0].data  # type: Optional[List[Tuple[str, str]]]
        
        

    def prepare_input_for_database(
        self,
        input: List[str],
        **kwargs: Any,
    ) -> List[str]:
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
    ) -> str:
        """Process the output of a generative model."""

        return [(str(output[0]), "str")]

    def process_output_from_database(
        self,
        output: List[str],
        **kwargs: Any,
    ) -> List[str]:
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
        input: List[str],
        **kwargs: Any,
    ) -> List[str]:
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
