from DashAI.back.models.base_generative_model import BaseGenerativeModel


class ImageGenerationModel(BaseGenerativeModel):
    """Class for models associated to ImageGenerationTasks."""

    COMPATIBLE_COMPONENTS = ["ImageGenerationTask"]
