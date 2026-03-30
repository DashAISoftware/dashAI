from typing import List, Optional

from pydantic import BaseModel


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
    configType: str  # noqa: N815


NODES: List[NodeDefinition] = [
    NodeDefinition(
        type="DataSelector",
        name="Data Selector",
        icon="FolderIcon",
        requiresConfiguration=True,
        source=True,
        target=False,
        predecessors=[],
        successors=["DataExploration", "Train", "SplitData"],
        description=(
            "Loads a dataset stored in the system to be used in the pipeline."
        ),
        output="Dataset object",
        configType="custom",
    ),
    NodeDefinition(
        type="DataExploration",
        name="Data Exploration",
        icon="InsertChartIcon",
        requiresConfiguration=True,
        source=False,
        target=True,
        predecessors=["DataSelector"],
        successors=[],
        description=(
            "Visualize and analyze your dataset to gain insights "
            "into its structure and content."
        ),
        input="Dataset object",
        configType="custom",
    ),
    NodeDefinition(
        type="SplitData",
        name="Split Data",
        icon="CallSplitIcon",
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["DataSelector"],
        successors=["TaskAndModel"],
        description=(
            "Configures the partition of the dataset into "
            "train / validation / test splits."
        ),
        input="Dataset object",
        output="Split dataset subsets",
        configType="custom",
    ),
    NodeDefinition(
        type="TaskAndModel",
        name="Task & Model",
        icon="ModelTrainingIcon",
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["SplitData"],
        successors=["MetricsEval", "Prediction"],
        description=(
            "Selects the ML task and model, configures hyper-parameters, "
            "and trains the model on the split data."
        ),
        input="Split dataset subsets",
        output="Trained model object",
        configType="custom",
    ),
    NodeDefinition(
        type="MetricsEval",
        name="Metrics",
        icon="AssessmentIcon",
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["TaskAndModel"],
        successors=["Prediction"],
        description=(
            "Evaluates the trained model using the selected metricson each data split."
        ),
        input="Trained model and split data",
        output="Evaluation results",
        configType="custom",
    ),
    NodeDefinition(
        type="Train",
        name="Train Model",
        icon="SettingsIcon",
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["DataSelector"],
        successors=["Prediction"],
        description=(
            "Trains a model using a selected dataset, with configurable "
            "columns, splits, task, model, and metrics."
        ),
        input="Dataset object",
        output="Trained model object and evaluation results",
        configType="custom",
    ),
    NodeDefinition(
        type="Prediction",
        name="Prediction",
        icon="EmojiObjectsIcon",
        requiresConfiguration=False,
        source=False,
        target=True,
        predecessors=["Train", "RetrieveModel", "TaskAndModel", "MetricsEval"],
        successors=[],
        description="Generates predictions using a trained model.",
        input="Trained model and dataset object",
        configType="custom",
    ),
    NodeDefinition(
        type="RetrieveModel",
        name="Retrieve Model",
        icon="ManageHistoryIcon",
        requiresConfiguration=True,
        source=True,
        target=True,
        predecessors=["DataSelector"],
        successors=["Prediction"],
        description="Loads a trained model from saved pipelines.",
        input="Dataset object",
        output="Trained model object",
        configType="custom",
    ),
]

NODE_TYPES = [node.model_dump() for node in NODES]
