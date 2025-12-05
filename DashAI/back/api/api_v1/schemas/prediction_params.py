from pydantic import BaseModel


class PredictionCreationParams(BaseModel):
    run_id: int
