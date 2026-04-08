from DashAI.back.models.base_model import BaseModel


class TranslationModel(BaseModel):
    """Base class for models that perform text translation tasks.

    Concrete translation models must extend this class and implement ``save``,
    ``load``, and ``train``. Compatible with ``TranslationTask``.
    """

    COMPATIBLE_COMPONENTS = ["TranslationTask"]
