from DashAI.back.models.base_model import BaseModel


class TabularClassificationModel(BaseModel):
    """Class for models associated to ClassificationTask."""

    COMPATIBLE_COMPONENTS = ["ClassificationTask"]
