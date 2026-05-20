"""Statistical tests endpoints"""

import logging
from typing import Dict, List

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from scipy import stats

from DashAI.back.api.api_v1.schemas.statistical_tests_params import (
    NormalityCheckRequest,
    NormalityCheckResponse,
    NormalityTestResult,
    PairwiseResultResponse,
    StatisticalTestRequest,
    StatisticalTestResponse,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/normality-check",
    response_model=NormalityCheckResponse,
    status_code=status.HTTP_200_OK,
)
async def check_normality(request: NormalityCheckRequest) -> NormalityCheckResponse:
    """Check normality for each run individually using Shapiro-Wilk test.

    For each run, performs a Shapiro-Wilk normality test on its fold metrics.
    Data is considered normal if p-value > 0.05.
    Overall result is normal only if ALL runs' metrics are normally distributed.

    Parameters
    ----------
    request : NormalityCheckRequest
        Request containing metric name, split, run IDs, and fold metrics.

    Returns
    -------
    NormalityCheckResponse
        Response with overall is_normal flag and individual results per run.

    Raises
    ------
    HTTPException
        If fold_metrics is empty or contains insufficient data.
    """
    try:
        if not request.fold_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fold_metrics cannot be empty",
            )

        results_by_run: List[NormalityTestResult] = []

        # Test normality for each run individually
        for run_id in request.run_ids:
            metrics = request.fold_metrics.get(run_id, [])

            if not metrics:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No metrics found for run {run_id}",
                )

            if len(metrics) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Run {run_id}: At least 3 data points required for "
                    f"normality test. Got {len(metrics)}",
                )

            # Perform Shapiro-Wilk normality test for this run
            metrics_array = np.array(metrics, dtype=float)
            _, p_value = stats.shapiro(metrics_array)

            # Data is considered normal if p-value > 0.05
            is_normal = p_value > 0.05

            results_by_run.append(
                NormalityTestResult(
                    run_id=run_id,
                    p_value=float(p_value),
                    is_normal=is_normal,
                )
            )

            log.info(
                f"Normality test for run '{run_id}', "
                f"metric '{request.metric_name}' ({request.metric_split} split): "
                f"p_value={p_value:.4f}, is_normal={is_normal}"
            )

        # Overall result: normal only if ALL runs are normal
        overall_is_normal = all(result.is_normal for result in results_by_run)

        return NormalityCheckResponse(
            is_normal=overall_is_normal,
            results_by_run=results_by_run,
            test_used="shapiro_wilk",
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error checking normality: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking normality: {str(e)}",
        ) from e


# Tests that trigger automatic post-hoc when significant
POSTHOC_MAP = {
    "FriedmanTest": "NemenyiTest",
    "AnovaTest": "TukeyHSDTest",
}


@router.post(
    "/run",
    response_model=StatisticalTestResponse,
    status_code=status.HTTP_200_OK,
)
async def run_statistical_test(
    request: StatisticalTestRequest,
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> StatisticalTestResponse:
    """Run a statistical test on fold metrics from selected runs.

    Automatically runs the appropriate post-hoc test (Nemenyi after Friedman,
    Tukey HSD after ANOVA) when the primary test is significant.
    PairwiseWilcoxon already includes pairwise comparisons with Holm correction
    and does not require a separate post-hoc step.

    Parameters
    ----------
    request : StatisticalTestRequest
        Request containing test name, metric, run IDs, fold metrics, alpha,
        and optional extra params (e.g. alternative hypothesis).

    Returns
    -------
    StatisticalTestResponse
        Test result including statistic, p-value, interpretation,
        and optional pairwise post-hoc results.

    Raises
    ------
    HTTPException
        400 if the test name is unknown or inputs are invalid.
        500 on internal error.
    """
    try:
        if not request.fold_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fold_metrics cannot be empty",
            )

        # Resolve test class from registry
        try:
            test_instance = component_registry[request.test_name]()
        except KeyError as key_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown statistical test: '{request.test_name}'. ",
            ) from key_error

        # Build scores dict keyed by run name for readability in results
        # Use run_id as key if no name mapping is available
        scores: Dict[str, List[float]] = {
            run_id: request.fold_metrics[run_id]
            for run_id in request.run_ids
            if run_id in request.fold_metrics
        }

        if len(scores) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least two runs with fold metrics are required.",
            )

        # Run the primary test, forwarding any extra params
        result: StatisticalTestResult = test_instance.run(
            scores=scores,
            alpha=request.alpha,
            **(request.params or {}),
        )

        # Run post-hoc automatically if the primary test is significant
        # and a post-hoc exists for this test
        posthoc_results = None
        if result.significant and request.test_name in POSTHOC_MAP:
            posthoc_test_name = POSTHOC_MAP[request.test_name]
            try:
                posthoc_instance = component_registry[posthoc_test_name]()

                # Pass precalculated omnibus values to avoid recomputing
                posthoc_result: StatisticalTestResult = posthoc_instance.run(
                    scores=scores,
                    alpha=request.alpha,
                    statistic=result.statistic,
                    p_value=result.p_value,
                )

                if posthoc_result.posthoc:
                    posthoc_results = [
                        PairwiseResultResponse(
                            run_1=pr.run_1,
                            run_2=pr.run_2,
                            p_value=pr.p_value,
                            significant=pr.significant,
                        )
                        for pr in posthoc_result.posthoc
                    ]
            except Exception as e:
                log.warning(f"Post-hoc test failed, skipping: {str(e)}")

        # Also expose pairwise results from tests that include them directly
        # (PairwiseWilcoxon, NemenyiTest, TukeyHSDTest when called directly)
        if posthoc_results is None and result.posthoc:
            posthoc_results = [
                PairwiseResultResponse(
                    run_1=pr.run_1,
                    run_2=pr.run_2,
                    p_value=pr.p_value,
                    significant=pr.significant,
                )
                for pr in result.posthoc
            ]

        log.info(
            f"Statistical test '{request.test_name}' completed: "
            f"p={result.p_value:.4f}, significant={result.significant}"
        )

        return StatisticalTestResponse(
            test_name=result.test_name,
            statistic=result.statistic,
            p_value=result.p_value,
            significant=result.significant,
            alpha=result.alpha,
            interpretation=result.interpretation,
            details=result.details,
            posthoc=posthoc_results,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error running statistical test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running statistical test: {str(e)}",
        ) from e
