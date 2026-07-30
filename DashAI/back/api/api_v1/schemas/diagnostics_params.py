from typing import Literal, Optional

from pydantic import BaseModel


class DiagnosticParams(BaseModel):
    """Body of a diagnostic creation request."""

    run_id: int
    diagnostic_name: str
    parameters: dict = {}
    split: Literal["train", "validation", "test"] = "test"
    name: Optional[str] = None
