from DashAI.back.models.base_generative_model import BaseGenerativeModel


class TextToImageGenerationTaskModel(BaseGenerativeModel):
    """Class for models associated to text to image generation task."""

    COMPATIBLE_COMPONENTS = ["TextToImageGenerationTask"]
