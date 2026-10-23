from DashAI.back.models.base_model import BaseModel


class RegressionModel(BaseModel):
    """Base class for models that perform regression tasks.

    Concrete regression models must extend this class and implement ``save``,
    ``load``, and ``train``. Compatible with ``RegressionTask``.
    """

    COMPATIBLE_COMPONENTS = ["RegressionTask"]
