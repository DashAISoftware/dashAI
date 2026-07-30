from typing import Literal

from pydantic import BaseModel


class DiagnosticParams(BaseModel):
    """Body of a diagnostic creation request.

    A diagnostic is identified by its component and the split it describes, so
    it carries no user supplied name.
    """

    run_id: int
    diagnostic_name: str
    parameters: dict = {}
    split: Literal["train", "validation", "test"] = "test"
