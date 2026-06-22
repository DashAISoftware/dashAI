from typing import List, Optional

from pydantic import BaseModel

from DashAI.back.pipeline.contracts import contracts_to_node_definitions


class NodeDefinition(BaseModel):
    type: str
    name: str
    icon: str
    requiresConfiguration: bool
    source: bool
    target: bool
    predecessors: List[str]
    successors: List[str]
    description: str
    input: Optional[str] = None
    output: Optional[str] = None
    sourceHandles: int = 1
    maxInputs: Optional[int] = 1
    maxOutputs: Optional[int] = None
    configType: str


NODES: List[NodeDefinition] = contracts_to_node_definitions()

NODE_TYPES = [node.model_dump() for node in NODES]
