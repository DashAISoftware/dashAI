"""Schemas for statistical tests endpoints."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class NormalityCheckRequest(BaseModel):
    """Request schema for normality check endpoint."""

    metric_name: str
    metric_split: str
    run_ids: List[int]
    fold_metrics: Dict[str, List[float]]


class NormalityTestResult(BaseModel):
    """Normality test result for a single run."""

    run_id: int
    p_value: float
    is_normal: bool


class NormalityCheckResponse(BaseModel):
    """Response schema for normality check endpoint."""

    is_normal: bool
    results_by_run: List[NormalityTestResult]
    test_used: str = "shapiro_wilk"


class StatisticalTestRequest(BaseModel):
    """Request schema for running a statistical test."""

    test_name: str
    metric_name: str
    metric_split: str
    run_ids: List[int]
    fold_metrics: Dict[str, List[float]]
    alpha: Optional[float] = 0.05
    # Extra kwargs forwarded to the test's run() method (e.g. alternative)
    params: Optional[Dict] = {}


class PairwiseResultResponse(BaseModel):
    """Single pairwise comparison result from a post-hoc test."""

    run_1: int
    run_2: int
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
