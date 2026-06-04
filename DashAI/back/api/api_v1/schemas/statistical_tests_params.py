"""Schemas for statistical tests endpoints."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class StatisticalTestRequest(BaseModel):
    """Request schema for running a statistical test."""

    test_name: str
    metric_name: str
    metric_split: str
    run_ids: List[int]
    run_names: Dict[
        str, str
    ]  # Mapping of run_id to run_name (e.g. {"1": "Model A", "2": "Model B"})
    fold_metrics: Dict[str, List[float]]
    alpha: Optional[float] = 0.05
    # Extra kwargs forwarded to the test's run() method (e.g. alternative)
    params: Optional[Dict] = {}


class PairwiseResultResponse(BaseModel):
    """Single pairwise comparison result from a post-hoc test."""

    run_1: int
    run_1_name: Optional[str] = None  # Display name for run_1
    run_2: int
    run_2_name: Optional[str] = None  # Display name for run_2
    p_value: float
    significant: bool


class StatisticalTestResponse(BaseModel):
    """Response schema for statistical test results."""

    test_name: str
    statistic: Optional[float] = None
    p_value: Optional[float] = None
    significant: bool
    alpha: float
    details: Optional[Dict] = None
    # Populated for post-hoc tests (Nemenyi, Tukey, PairwiseWilcoxon)
    posthoc: Optional[List[PairwiseResultResponse]] = None
