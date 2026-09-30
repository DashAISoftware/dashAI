from typing import List, Optional

from pydantic import BaseModel

from DashAI.back.pipeline.contracts import contracts_to_node_definitions


class NodeDefinition(BaseModel):
    type: str
    name: str
    icon: str
    requiresConfiguration: bool  # noqa: N815
    source: bool
    target: bool
    predecessors: List[str]
    successors: List[str]
    description: str
    input: Optional[str] = None
    output: Optional[str] = None
    sourceHandles: int = 1  # noqa: N815
    maxInputs: Optional[int] = 1  # noqa: N815
    maxOutputs: Optional[int] = None  # noqa: N815
    configType: str  # noqa: N815


NODES: List[NodeDefinition] = contracts_to_node_definitions()

NODE_TYPES = [node.model_dump() for node in NODES]
