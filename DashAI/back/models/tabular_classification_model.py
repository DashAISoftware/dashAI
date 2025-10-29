from DashAI.back.models.base_model import BaseModel


class ClassificationModel(BaseModel):
    """Class for models associated to ClassificationTask."""

    COMPATIBLE_COMPONENTS = ["ClassificationTask"]
