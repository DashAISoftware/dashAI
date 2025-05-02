from DashAI.back.models.base_generative_model import BaseGenerativeModel

class LLMGenerationModel(BaseGenerativeModel):
    """Class for models associated to LLMGenerationTask."""

    COMPATIBLE_COMPONENTS = ["LLMGenerationTask"]

