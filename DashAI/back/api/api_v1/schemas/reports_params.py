from typing import Literal

from pydantic import BaseModel


class ReportParams(BaseModel):
    """Body of a report creation request.

    A report is identified by its component and the split it describes, so
    it carries no user supplied name.
    """

    run_id: int
    report_name: str
    parameters: dict = {}
    split: Literal["train", "validation", "test"] = "test"


class PlotOverrideBody(BaseModel):
    """Request body for saving one plot override.

    Attributes
    ----------
    index : int
        Artifact index whose payload is being overridden.
    figure : object
        The edited plotly figure, either a JSON string or a dict.
    """

    index: int
    figure: object
