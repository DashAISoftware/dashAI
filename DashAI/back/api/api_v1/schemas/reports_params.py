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
