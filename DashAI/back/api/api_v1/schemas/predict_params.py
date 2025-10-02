from pydantic import BaseModel


class PredictParams(BaseModel):
    run_id: int


class RenameRequest(BaseModel):
    new_name: str


class FilterDatasetParams(BaseModel):
    run_id: int
