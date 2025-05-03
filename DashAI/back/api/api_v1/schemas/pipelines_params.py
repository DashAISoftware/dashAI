from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Step(BaseModel):
    id: str
    type: str
    label: str
    config: Optional[Dict[str, Any]]


class PipelineCreateParams(BaseModel):
    steps: Optional[List[Step]]


class PipelineUpdateParams(BaseModel):
    steps: Optional[List[Step]]
    exploration: Optional[Dict[str, Any]]
    train: Optional[Dict[str, Any]]
    prediction: Optional[Dict[str, Any]]
