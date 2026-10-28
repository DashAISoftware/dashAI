from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from DashAI.back.preprocessing.column_ref import ColumnRef, ConverterStep


class ModelSessionParams(BaseModel):
    # The old column fields (input_columns, output_columns,
    # input_column_refs) are refused rather than ignored.
    model_config = ConfigDict(extra="forbid")

    dataset_id: int
    task_name: str
    name: str
    # Role name to the role's columns, as the task declares its roles: refs
    # over the original columns or over the outputs of the preprocessing
    # steps.
    column_roles: Dict[str, List[ColumnRef]]
    train_metrics: List[str]
    validation_metrics: List[str]
    test_metrics: List[str]
    evaluation_strategy: str
    splits: str
    preprocessing: List[ConverterStep] = Field(default_factory=list)


class ColumnsValidationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_name: str
    dataset_id: int
    column_roles: Dict[str, List[ColumnRef]]
    # With preprocessing, the type of every input ref is taken from the
    # chain's estimated structure (see infer_structure).
    preprocessing: Optional[List[ConverterStep]] = None


class PreprocessingStructureParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: int
    task_name: str
    # Role name to the original columns the user gave the role. The roles the
    # task lets the preprocessing transform are the columns fed into the
    # chain; the others never enter it.
    column_roles: Dict[str, List[str]]
    steps: List[ConverterStep] = Field(default_factory=list)


class ModelSessionBulkDeleteParams(BaseModel):
    ids: List[int]


class SessionExportParams(BaseModel):
    run_ids: List[int]
    include_trained_models: bool = True
