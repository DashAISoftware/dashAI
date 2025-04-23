import base64
import io
import uuid
from typing import Any, List, Optional

from PIL import Image

from DashAI.back.tasks.base_generative_task import BaseGenerativeTask


class ImageGenerationTask(BaseGenerativeTask):
    """Base class for image generation tasks.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [str],
        "outputs_types": [Image],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    DESCRIPTION: str = "This task generates images based on the provided input text."

    DISPLAY_NAME: str = "Text to Image"

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
        save_dir = path / "generative-images"
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

    def process_output_from_database(self, output: List[str]) -> List[str]:
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
        encoded_images = []

        for image_path in output:
            if not image_path:
                encoded_images.append(None)
                continue

            with open(image_path, "rb") as image_file:
                buffer = io.BytesIO(image_file.read())
                buffer.seek(0)

                encoded_string = base64.b64encode(buffer.read()).decode("utf-8")
                encoded_images.append(encoded_string)

        return encoded_images
