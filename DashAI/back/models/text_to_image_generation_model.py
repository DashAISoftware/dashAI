from DashAI.back.models.base_generative_model import BaseGenerativeModel


class TextToImageGenerationTaskModel(BaseGenerativeModel):
    """Base class for models that generate images from text prompts.

    Concrete text-to-image models must extend this class and implement
    ``generate``. Compatible with ``TextToImageGenerationTask``.
    """

    COMPATIBLE_COMPONENTS = ["TextToImageGenerationTask"]
