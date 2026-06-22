from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Literal, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from DashAI.back.pipeline.validator.nodes_definitions import NodeDefinition

DataKind = Literal[
    "DatasetRef",
    "DatasetSplit",
    "ModelArtifact",
    "MetricsResult",
    "PredictionArtifact",
    "ExplorationResult",
    "Any",
]


class PortSpec(BaseModel):
    name: str
    kind: DataKind
    accepts: Optional[List[DataKind]] = None
    required: bool = True
    max_connections: Optional[int] = 1
    description: Optional[str] = None


class NodeContract(BaseModel):
    type: str
    name: str
    icon: str
    description: str
    requiresConfiguration: bool  # noqa: N815
    source: bool
    target: bool
    predecessors: List[str]
    successors: List[str]
    input: Optional[str] = None
    output: Optional[str] = None
    sourceHandles: int = 1  # noqa: N815
    maxInputs: Optional[int] = 1  # noqa: N815
    maxOutputs: Optional[int] = None  # noqa: N815
    configType: str = "custom"  # noqa: N815
    inputs: List[PortSpec]
    outputs: List[PortSpec]


NODE_CONTRACTS: List[NodeContract] = [
    NodeContract(
        type="DataSelector",
        name="Data Selector",
        icon="FolderIcon",
        description="Loads a dataset stored in the system to be used in the pipeline.",
        requiresConfiguration=True,
        source=True,
        target=False,
        predecessors=[],
        successors=["DataExploration", "Train", "SplitData"],
        output="Dataset object",
        sourceHandles=2,
        maxOutputs=2,
        inputs=[],
        outputs=[
            PortSpec(
                name="dataset",
                kind="DatasetRef",
                max_connections=2,
                description="Reference to the dataset loaded from storage.",
            )
        ],
    ),
    NodeContract(
        type="DataExploration",
        name="Data Exploration",
        icon="InsertChartIcon",
        description=(
            "Visualize and analyze your dataset to gain insights into its structure "
            "and content."
        ),
        requiresConfiguration=True,
        source=False,
        target=True,
        predecessors=["DataSelector"],
        successors=[],
        input="Dataset object",
        inputs=[
            PortSpec(
                name="dataset",
                kind="DatasetRef",
                description="Dataset used for exploration.",
            )
        ],
        outputs=[
            PortSpec(
                name="exploration",
                kind="ExplorationResult",
                description="Exploration outputs and charts.",
            )
        ],
    ),
    NodeContract(
        type="SplitData",
        name="Split Data",
        icon="CallSplitIcon",
        description=(
            "Configures the partition of the dataset into train / validation / test "
            "splits."
        ),
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["DataSelector"],
        successors=["TaskAndModel"],
        input="Dataset object",
        output="Split dataset subsets",
        sourceHandles=2,
        maxOutputs=2,
        inputs=[
            PortSpec(
                name="dataset",
                kind="DatasetRef",
                description="Dataset to split.",
            )
        ],
        outputs=[
            PortSpec(
                name="split",
                kind="DatasetSplit",
                max_connections=2,
                description="Train/validation/test splits.",
            )
        ],
    ),
    NodeContract(
        type="TaskAndModel",
        name="Task & Model",
        icon="ModelTrainingIcon",
        description=(
            "Selects the ML task and model, configures hyper-parameters, and trains "
            "the model on the split data."
        ),
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["SplitData"],
        successors=["MetricsEval", "Prediction"],
        input="Split dataset subsets",
        output="Trained model object",
        sourceHandles=2,
        maxOutputs=2,
        inputs=[
            PortSpec(
                name="split",
                kind="DatasetSplit",
                description="Split dataset used for training.",
            )
        ],
        outputs=[
            PortSpec(
                name="model",
                kind="ModelArtifact",
                max_connections=2,
                description="Trained model artifact.",
            )
        ],
    ),
    NodeContract(
        type="MetricsEval",
        name="Metrics",
        icon="AssessmentIcon",
        description="Evaluates the trained model using the selected metrics.",
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["TaskAndModel"],
        successors=["Prediction"],
        input="Trained model and split data",
        output="Model artifact (metrics stored in pipeline results)",
        maxInputs=2,
        inputs=[
            PortSpec(
                name="model",
                kind="ModelArtifact",
                max_connections=2,
                description="Model to evaluate.",
            )
        ],
        outputs=[
            PortSpec(
                name="model",
                kind="ModelArtifact",
                description="Model artifact passthrough for downstream nodes.",
            )
        ],
    ),
    NodeContract(
        type="Train",
        name="Train Model",
        icon="SettingsIcon",
        description=(
            "Trains a model using a selected dataset, with configurable columns, "
            "splits, task, model, and metrics."
        ),
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["DataSelector"],
        successors=["Prediction"],
        input="Dataset object",
        output="Trained model object and evaluation results",
        inputs=[
            PortSpec(
                name="dataset",
                kind="DatasetRef",
                description="Dataset used for training.",
            )
        ],
        outputs=[
            PortSpec(
                name="model",
                kind="ModelArtifact",
                description="Trained model artifact.",
            )
        ],
    ),
    NodeContract(
        type="Prediction",
        name="Prediction",
        icon="EmojiObjectsIcon",
        description="Generates predictions using a trained model.",
        requiresConfiguration=False,
        source=False,
        target=True,
        predecessors=["Train", "RetrieveModel", "TaskAndModel", "MetricsEval"],
        successors=[],
        input="Trained model and dataset object",
        inputs=[
            PortSpec(
                name="model",
                kind="ModelArtifact",
                description="Model used for predictions.",
            )
        ],
        outputs=[
            PortSpec(
                name="prediction",
                kind="PredictionArtifact",
                description="Prediction output artifact.",
            )
        ],
    ),
    NodeContract(
        type="RetrieveModel",
        name="Retrieve Model",
        icon="ManageHistoryIcon",
        description="Loads a trained model from saved pipelines.",
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["DataSelector"],
        successors=["Prediction"],
        input="Dataset object",
        output="Trained model object",
        inputs=[
            PortSpec(
                name="dataset",
                kind="DatasetRef",
                description="Dataset used for compatibility checks.",
            )
        ],
        outputs=[
            PortSpec(
                name="model",
                kind="ModelArtifact",
                description="Loaded model artifact.",
            )
        ],
    ),
]

NODE_CONTRACTS_MAP: Dict[str, NodeContract] = {
    contract.type: contract for contract in NODE_CONTRACTS
}


def get_contracts_payload() -> List[Dict[str, object]]:
    payload = [contract.model_dump() for contract in NODE_CONTRACTS]
    type_to_name = {contract.type: contract.name for contract in NODE_CONTRACTS}
    for entry in payload:
        entry["next"] = [type_to_name.get(t, t) for t in entry.get("successors", [])]
    return payload


def _resolve_port(
    ports: List[PortSpec], port_name: Optional[str], role: str
) -> PortSpec:
    if port_name:
        for port in ports:
            if port.name == port_name:
                return port
        raise ValueError(f"Unknown {role} port: {port_name}")
    if len(ports) == 1:
        return ports[0]
    raise ValueError(f"Ambiguous {role} port: specify a port name")


def validate_edge(
    source_type: str,
    target_type: str,
    source_port: Optional[str] = None,
    target_port: Optional[str] = None,
    source_current_outputs: Optional[int] = None,
    target_current_inputs: Optional[int] = None,
) -> Dict[str, object]:
    source_contract = NODE_CONTRACTS_MAP.get(source_type)
    target_contract = NODE_CONTRACTS_MAP.get(target_type)

    if source_contract is None:
        return _error_response(
            "Unknown source node type.",
            reason="UNKNOWN_SOURCE",
        )
    if target_contract is None:
        return _error_response(
            "Unknown target node type.",
            reason="UNKNOWN_TARGET",
        )

    if target_contract.predecessors and source_type not in target_contract.predecessors:
        return _error_response(
            f"{target_contract.name} does not accept {source_contract.name} as input.",
            reason="INVALID_PREDECESSOR",
        )
    if source_contract.successors and target_type not in source_contract.successors:
        return _error_response(
            f"{source_contract.name} cannot connect to {target_contract.name}.",
            reason="INVALID_SUCCESSOR",
        )

    try:
        target_port_spec = _resolve_port(
            target_contract.inputs, target_port, role="target"
        )
        if source_port:
            source_port_spec = _resolve_port(
                source_contract.outputs, source_port, role="source"
            )
        else:
            accepts = target_port_spec.accepts or [target_port_spec.kind]
            compatible = [
                port for port in source_contract.outputs if port.kind in accepts
            ]
            if len(compatible) == 1:
                source_port_spec = compatible[0]
            else:
                source_port_spec = _resolve_port(
                    source_contract.outputs, source_port, role="source"
                )
    except ValueError as exc:
        return _error_response(str(exc), reason="INVALID_PORT")

    if (
        target_port_spec.max_connections is not None
        and target_current_inputs is not None
        and target_current_inputs >= target_port_spec.max_connections
    ):
        return _error_response(
            f"{target_contract.name} does not allow more connections on this input.",
            reason="MAX_INPUTS_EXCEEDED",
            severity="warning",
            edge_color="#F57C00",
            edge_class="edge-warning",
        )

    if (
        source_current_outputs is not None
        and source_port_spec.max_connections is not None
        and source_current_outputs >= source_port_spec.max_connections
    ):
        return _error_response(
            f"{source_contract.name} does not allow more outputs on this port.",
            reason="MAX_OUTPUTS_EXCEEDED",
            severity="warning",
            edge_color="#F57C00",
            edge_class="edge-warning",
        )

    accepts = target_port_spec.accepts or [target_port_spec.kind]
    if source_port_spec.kind not in accepts:
        return _error_response(
            (
                f"{source_contract.name} outputs {source_port_spec.kind}, but "
                f"{target_contract.name} expects {', '.join(accepts)}."
            ),
            reason="TYPE_MISMATCH",
        )

    return {
        "ok": True,
        "severity": "info",
        "message": "Compatible connection.",
        "reason": None,
        "style": {
            "edgeColor": "#4CAF50",
            "edgeClass": "edge-ok",
        },
    }


def _error_response(
    message: str,
    reason: str,
    severity: str = "error",
    edge_color: str = "#D32F2F",
    edge_class: str = "edge-error",
) -> Dict[str, object]:
    return {
        "ok": False,
        "severity": severity,
        "message": message,
        "reason": reason,
        "style": {
            "edgeColor": edge_color,
            "edgeClass": edge_class,
        },
    }


def contracts_to_node_definitions() -> List["NodeDefinition"]:
    from DashAI.back.pipeline.validator.nodes_definitions import NodeDefinition

    definitions: List[NodeDefinition] = []
    for contract in NODE_CONTRACTS:
        definitions.append(
            NodeDefinition(
                type=contract.type,
                name=contract.name,
                icon=contract.icon,
                requiresConfiguration=contract.requiresConfiguration,
                source=contract.source,
                target=contract.target,
                predecessors=contract.predecessors,
                successors=contract.successors,
                description=contract.description,
                input=contract.input,
                output=contract.output,
                sourceHandles=contract.sourceHandles,
                maxInputs=contract.maxInputs,
                maxOutputs=contract.maxOutputs,
                configType=contract.configType,
            )
        )
    return definitions
