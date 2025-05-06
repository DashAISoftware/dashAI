import uuid
from typing import Any, List, Optional

from PIL import Image

from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class ControlNetTask(BaseGenerativeTask):
    """Base class for image generation tasks using ControlNet.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [Image.Image, str],
        "outputs_types": [Image.Image],
        "inputs_cardinality": 2,
        "outputs_cardinality": None,
    }

    DESCRIPTION: str = (
        "This task generates images based on the provided input text and image."
    )

    DISPLAY_NAME: str = "ControlNet"

    def prepare_for_task(self, input: tuple[str, str]) -> tuple[Image.Image, str]:
        """Change the inputs to suit the image generation task.

        Parameters
        ----------
        input : List[str, str]
            List of inputs to be processed

        Returns
        -------
        str
            Input with the new types
        """

        # Read the image from the path
        image = Image.open(input[0])
        prompt = input[1]

        return [image, prompt]

    def prepare_input_for_database(
        self, input: tuple[bytes, str], **kwargs: Any
    ) -> tuple[str, str]:
        """Prepare the input for the database.

        Parameters
        ----------
        input : tuple[Image, str]
            Image and prompt to be processed

        Returns
        -------
        tuple[str, str]
            Image path and prompt
        """

        path = kwargs.get("path")
        path = path / "images"

        # Save the image to a temporary file
        image_path = path / f"{uuid.uuid4()}.png"
        with open(image_path, "wb") as f:
            f.write(input[0])

        return [str(image_path), input[1]]

    def process_output(
        self,
        output: List[Any],
        path: Optional[str] = None,
    ) -> List[str]:
        """Process the output of a generative model.

        Parameters
        ----------
        output : List[Any]
            list of images to be processed
        path : Optional[str], optional
            Path to save the output, by default None

        Returns
        -------
        List[str]
            List of paths to the processed images
        """
        save_dir = path / "images"
        if not save_dir.exists():
            save_dir.mkdir(parents=True)

        image_paths = []

        for img in output:
            # Generate a unique file name
            file_name = str(uuid.uuid4())

            image_path = save_dir / f"{file_name}.png"

            # Save the image
            img.save(image_path, format="PNG")

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

        output = list(map(lambda x: x.split("\\")[-1], output)) if output else None

        return output

    def process_input_from_database(self, input: List[str]) -> List[str]:
        """Process the input of an image generation model from the database.

        Parameters
        ----------
        input : List[str]
            List of paths to the images

        Returns
        -------
        List[str]
            List of image names
        """

        input_processed = []
        for ip in input:
            if ip.endswith(".png") or ip.endswith(".jpg"):
                # Extract the image name from the path
                ip = ip.split("\\")[-1]
                input_processed.append(ip)
            else:
                # If the input is not an image, just append it as is
                input_processed.append(ip)

        print(input_processed)

        return input_processed
