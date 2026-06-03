"""Statistical tests endpoints"""

import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di

from DashAI.back.api.api_v1.schemas.statistical_tests_params import (
    PairwiseResultResponse,
    StatisticalTestRequest,
    StatisticalTestResponse,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.statistical_tests.base_statistical_test import BaseStatisticalTest
from DashAI.back.statistical_tests.statistical_test_result import StatisticalTestResult

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()

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
            test_instance: BaseStatisticalTest = component_registry[request.test_name][
                "class"
            ]()
        except KeyError as key_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown statistical test: '{request.test_name}'. ",
            ) from key_error

        # Build scores dict keyed by run name for readability in results
        # Use run_id as key if no name mapping is available
        scores: Dict[str, List[float]] = {
            run_id: request.fold_metrics[str(run_id)]
            for run_id in request.run_ids
            if str(run_id) in request.fold_metrics
        }

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
                posthoc_instance: BaseStatisticalTest = component_registry[
                    posthoc_test_name
                ]["class"]()

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
                            run_1_name=request.run_names.get(str(pr.run_1), None),
                            run_2=pr.run_2,
                            run_2_name=request.run_names.get(str(pr.run_2), None),
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
                    run_1_name=request.run_names.get(str(pr.run_1), None),
                    run_2=pr.run_2,
                    run_2_name=request.run_names.get(str(pr.run_2), None),
                    p_value=pr.p_value,
                    significant=pr.significant,
                )
                for pr in result.posthoc
            ]

        log.info(
            f"Statistical test '{request.test_name}' completed: "
            f"p={result.p_value}, significant={result.significant}"
        )

        return StatisticalTestResponse(
            test_name=request.test_name,
            statistic=result.statistic,
            p_value=result.p_value,
            significant=result.significant,
            alpha=result.alpha,
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
