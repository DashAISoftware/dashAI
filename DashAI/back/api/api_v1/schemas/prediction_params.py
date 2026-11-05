from typing import Optional

from pydantic import BaseModel, Field


class PredictionCreationParams(BaseModel):
    run_id: int
    dataset_id: Optional[int] = None
    split: Optional[str] = None
    # Steps past the end of the training series, for a task that predicts by
    # horizon; a task that predicts rows takes a dataset instead.
    horizon: Optional[int] = Field(default=None, ge=1)
