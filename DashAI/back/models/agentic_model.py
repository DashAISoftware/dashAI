from DashAI.back.models.base_agentic_model import BaseAgenticModel


class AgenticModel(BaseAgenticModel):
    """Base class for models that are used in agentic modality.

    Concrete models in agentic modality must extend this class and implement
    ``generate`` and ``resume``.
    """

    COMPATIBLE_COMPONENTS = []
