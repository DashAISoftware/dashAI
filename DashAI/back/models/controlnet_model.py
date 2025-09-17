from DashAI.back.models.base_generative_model import BaseGenerativeModel


class ControlNetModel(BaseGenerativeModel):
    """Class for models associated to ControlNet Tasks."""

    COMPATIBLE_COMPONENTS = ["ControlNetTask"]
