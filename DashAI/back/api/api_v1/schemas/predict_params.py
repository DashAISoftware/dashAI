from typing import Optional

from pydantic import BaseModel, Field


class PredictParams(BaseModel):
    run_id: int
    forecast_periods: Optional[int] = Field(
        default=None,
        description="Number of future periods to forecast (ForecastingTask only). "
        "If provided, timestamps will be generated automatically from the last "
        "training date.",
        gt=0,
        le=1000,
    )


class RenameRequest(BaseModel):
    new_name: str


class FilterDatasetParams(BaseModel):
    run_id: int
