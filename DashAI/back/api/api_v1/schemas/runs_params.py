from typing import Union

from pydantic import BaseModel


class RunParams(BaseModel):
    experiment_id: int
    model_name: str
    name: str
    parameters: dict
    optimizer_name: str
    optimizer_parameters: dict
    plot_history_path: str
    plot_slice_path: str
    plot_contour_path: str
    plot_importance_path: str
    goal_metric: str
    description: Union[str, None] = None
