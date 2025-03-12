from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Step(BaseModel):
    id: str
    type: str
    label: str
    config: Optional[Dict[str, Any]]


class PipelineCreateParams(BaseModel):
    name: str
    description: Optional[str]
    steps: Optional[List[Step]]


class PipelineUpdateParams(BaseModel):
    name: Optional[str]
    description: Optional[str]
    steps: Optional[List[Step]]
