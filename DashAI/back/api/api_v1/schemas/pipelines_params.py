from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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


class ValidateNodeParams(BaseModel):
    type: str
    config: Dict[str, Any]


class ValidatePipelineParams(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
