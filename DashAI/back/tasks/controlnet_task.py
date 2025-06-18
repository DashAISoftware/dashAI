import os
import uuid
from typing import Any, List, Tuple, Union

from PIL import Image

from DashAI.back.dependencies.database.models import ProcessData
from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class ControlNetTask(BaseGenerativeTask):
    """Base class for image generation tasks using ControlNet.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [Image.Image, str],
        "outputs_types": [Image.Image],
        "inputs_cardinality": 2,
        "outputs_cardinality": "n",
    }

    DISPLAY_NAME: str = "ControlNet"
    DESCRIPTION: str = (
        "This task generates images based on the provided input text and image."
    )

    def prepare_for_task(
        self,
        input: List[ProcessData],
        **kwargs: Any,
    ) -> Tuple[Image.Image, str]:
        """Change the inputs to suit the image generation task.

        Parameters
        ----------
        input : List[ProcessData]
            Input data to be prepared, a list of ProcessData objects

        Returns
        -------
        str
            Input with the new types
        """

        # Read the image from the path and ensure image is first, text second
        image = None
        text = None
        for ip in input:
            if ip.data_type == "Image":
                image = Image.open(ip.data)
            elif ip.data_type == "str":
                text = ip.data
            else:
                raise ValueError(f"Unsupported data type: {ip.data_type}")

        if image is None or text is None:
            raise ValueError("Both image and text inputs are required.")

        return (image, text)

    def prepare_input_for_database(
        self,
        input: List[Union[bytes, str]],
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Prepare the input for the database.

        Parameters
        ----------
        input : List[Union[bytes, str]]
            List containing the image bytes and the prompt string.

        Returns
        -------
        List[Tuple[str, str]]
            Image path and prompt
        """

        path = kwargs.get("images_path")
        if not path.exists():
            path.mkdir(parents=True)

        # Save the image to a temporary file
        prepared_input = []
        for _, item in enumerate(input):
            if isinstance(item, bytes):
                # Generate a unique file name
                file_name = str(uuid.uuid4())
                image_path = path / f"{file_name}.png"

                # Save the image bytes to the file
                with open(image_path, "wb") as f:
                    f.write(item)
                prepared_input.append((str(image_path), "Image"))
            elif isinstance(item, str):
                # Keep the text as is
                prepared_input.append((item, "str"))
            else:
                raise ValueError(f"Unsupported input type: {type(item)}")

        return prepared_input

    def process_output(
        self,
        output: List[Any],
        **kwargs: Any,
    ) -> List[Tuple[str, str]]:
        """Process the output of a generative model.

        Parameters
        ----------
        output : List[Any]
            list of images to be processed
        path : Optional[str], optional
            Path to save the output, by default None

        Returns
        -------
        List[Tuple[str, str]]
            Processed output data as a list of tuples containing the data and its type
        """
        save_dir = kwargs.get("images_path")
        if not save_dir.exists():
            save_dir.mkdir(parents=True)

        image_paths = []

        for img in output:
            # Generate a unique file name
            file_name = str(uuid.uuid4())

            image_path = save_dir / f"{file_name}.png"

            # Save the image
            img.save(image_path, format="PNG")

            image_paths.append((str(image_path), "Image"))

        return image_paths

    def process_output_from_database(
        self,
        output: List[ProcessData],
        **kwargs: Any,
    ) -> List[ProcessData]:
        """Process the output of an image generation model from the database.

        Parameters
        ----------
        output : List[ProcessData]
            Output data to be processed, a list of ProcessData objects

        Returns
        -------
        List[ProcessData]
            Processed output data, a list of ProcessData objects
        """

        for op in output:
            op.data = os.path.basename(op.data)

        return output

    def process_input_from_database(
        self,
        input: List[ProcessData],
        **kwargs: Any,
    ) -> List[ProcessData]:
        """Process the input of an image generation model from the database.

        Parameters
        ----------
        input : List[ProcessData]
            Input data to be processed, a list of ProcessData objects

        Returns
        -------
        List[ProcessData]
            Processed input data, a list of ProcessData objects
        """

        for ip in input:
            if ip.data_type == "Image":
                # Get the filename from the path
                ip.data = os.path.basename(ip.data)

            elif ip.data_type == "str":
                # Keep the text as is
                ip.data = ip.data
            else:
                raise ValueError(f"Unsupported data type: {ip.data_type}")

        return input
