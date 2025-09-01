from DashAI.back.models.base_generative_model import BaseGenerativeModel


class TextToTextGenerationTaskModel(BaseGenerativeModel):
    """Class for models associated to TextToTextGenerationTask."""

    COMPATIBLE_COMPONENTS = ["TextToTextGenerationTask"]
