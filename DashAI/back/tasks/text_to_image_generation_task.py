import os
import uuid
from typing import Any, List

from PIL import Image

from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class TextToImageGenerationTask(BaseGenerativeTask):
    """Base class for image generation tasks.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [str],
        "outputs_types": [Image.Image],
        "inputs_cardinality": 1,
        "outputs_cardinality": None,
    }

    DESCRIPTION: str = "This task generates images based on the provided input text."

    DISPLAY_NAME: str = "Text to Image"

    def prepare_for_task(
        self,
        input: List[str],
        **kwargs: Any,
    ) -> str:
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
        return input[0]

    def prepare_input_for_database(
        self,
        input: List[str],
        **kwargs: Any,
    ) -> List[str]:
        """Prepare the input for the database.

        Parameters
        ----------
        input : str
            Input to be changed

        Returns
        -------
        str
            Input with the new types
        """
        return input

    def process_output(
        self,
        output: List[Any],
        **kwargs: Any,
    ) -> List[str]:
        """Process the output of a generative model.

        Parameters
        ----------
        output : List[Any]
            list of images to be processed

        Returns
        -------
        List[str]
            List of paths to the processed images
        """
        save_dir = kwargs.get("images_path")

        if not save_dir.exists():
            save_dir.mkdir(parents=True)

        image_paths = []

        for img in output:
            # Generate a unique file name
            file_name = str(uuid.uuid4())

            image_path = f"{file_name}.png"

            # Save the image
            img.save(save_dir / image_path, format="PNG")

            image_paths.append(str(image_path))

        return image_paths

    def process_output_from_database(
        self,
        output: List[str],
        **kwargs: Any,
    ) -> List[str]:
        """Process the output of an image generation model from the database.

        Parameters
        ----------
        output : List[str]
            List of paths to the images

        Returns
        -------
        List[str]
            List of base64 encoded images
        """

        output = [os.path.basename(x) for x in output] if output else None

        return output

    def process_input_from_database(
        self,
        input: List[str],
        **kwargs: Any,
    ) -> List[str]:
        """Process the input of an image generation model from the database.

        Parameters
        ----------
        input : List[str]
            List of paths to the images

        Returns
        -------
        List[str]
            List of base64 encoded images
        """
        return input
