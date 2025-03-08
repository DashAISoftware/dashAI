from typing import Dict

from pydantic import BaseModel, ConfigDict


class DatasetParams(BaseModel):
    model_config = ConfigDict(extra="allow")

    dataloader: str
    name: str


class ColumnSpecItemParams(BaseModel):
    type: str
    dtype: str


class ColumnsSpecParams(BaseModel):
    columns: Dict[str, ColumnSpecItemParams]


class DatasetUpdateParams(BaseModel):
    name: str = None
    columns: Dict[str, ColumnSpecItemParams] = None
