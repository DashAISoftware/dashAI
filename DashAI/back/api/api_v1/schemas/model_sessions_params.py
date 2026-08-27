from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SessionConverterParams(BaseModel):
    converter: str
    params: Dict[str, Any] = {}
    columns: List[str] = []
    target_column: Optional[str] = None


class UpdateConvertersParams(BaseModel):
    converters: List[SessionConverterParams] = []


class ModelSessionParams(BaseModel):
    dataset_id: int
    task_name: str
    name: str
    input_columns: List[str] = []
    output_columns: List[str] = []
    train_metrics: List[str]
    validation_metrics: List[str]
    test_metrics: List[str]
    evaluation_strategy: str
    splits: str
    converters: List[SessionConverterParams] = []


class ColumnsValidationParams(BaseModel):
    task_name: str
    dataset_id: int
    inputs_columns: List[str]
    outputs_columns: List[str]
    model_session_id: Optional[int] = None


class ModelSessionBulkDeleteParams(BaseModel):
    ids: List[int]
