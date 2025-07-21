from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Step(BaseModel):
    id: str
    type: str
    label: str
    config: Optional[Dict[str, Any]]


class PipelineCreateParams(BaseModel):
    name: Optional[str]
    steps: Optional[List[Step]]
    edges: Optional[List[Dict[str, Any]]]


class PipelineUpdateParams(BaseModel):
    name: Optional[str]
    steps: Optional[List[Step]]
    edges: Optional[List[Dict[str, Any]]]

class DatasetFilterParams(BaseModel):
    dataset_id: int
    pipeline_id: Optional[int] = None
