import uuid
from typing import Any, Optional

from DashAI.back.tasks.base_generative_task import BaseGenerativeTask
from DashAI.back.tasks.base_task import BaseTask


class ImageGenerationTask(BaseGenerativeTask):
    """Base class for image generation tasks.

    Here you can change the methods provided by class Task.
    """

    metadata: dict = {
        "inputs_types": [str],
        "outputs_types": [str],
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
        output: Any,
        path: Optional[str] = None,
    ) -> str:
        """Process the output of a generative model.

        file_name (Str): Indicates the name of the file.
        path (Str): Indicates the path where the output will be stored.
        """
        save_dir = path / "generative-images"
        if not save_dir.exists():
            save_dir.mkdir(parents=True)

        # Generate a unique file name
        file_name = str(uuid.uuid4())

        image_path = save_dir / f"{file_name}.png"

        # Save the image
        output.save(image_path, format="PNG")

        return str(image_path)
