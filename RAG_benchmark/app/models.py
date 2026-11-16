"""Pydantic data models for benchmark results.

Each benchmark execution produces structured records that can be
serialised to JSON and flattened to CSV.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComponentBenchmarkResult(BaseModel):
    """Result of a single component-level benchmark execution."""

    component_name: str
    params: Dict[str, Any]
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None
    output_size: Optional[int] = None
    iteration: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class TurnRecord(BaseModel):
    """A single conversation turn in a pipeline benchmark."""

    turn_number: int
    user_message: str
    assistant_response: str
    retrieval_time_ms: float = 0.0
    transformation_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    total_turn_time_ms: float
    chunks_retrieved: int
    queries: List[str] = Field(default_factory=list)
    retrieved_chunks: Any = Field(default_factory=dict)
    prompt_length_chars: int
    response_length_chars: int
    error: Optional[str] = None


class PipelineRunResult(BaseModel):
    """Complete result of one pipeline benchmark execution."""

    pipeline_name: str
    pipeline_config: Dict[str, Any]
    document_ids: List[int]
    turns: List[TurnRecord]
    total_time_ms: float
    avg_retrieval_time_ms: float
    avg_generation_time_ms: float
    avg_turn_time_ms: float
    total_chunks_retrieved: int
    success: bool
    avg_transformation_time_ms: float = 0.0
    error_message: Optional[str] = None
    #: True when the pipeline was skipped (already passed in a prior run).
    skipped: bool = False
    iteration: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class BenchmarkSuiteResult(BaseModel):
    """Top-level container for all benchmark results."""

    suite_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    config_snapshot: Dict[str, Any]
    component_results: List[ComponentBenchmarkResult] = []
    pipeline_results: List[PipelineRunResult] = []
    summary: Optional[Dict[str, Any]] = None
