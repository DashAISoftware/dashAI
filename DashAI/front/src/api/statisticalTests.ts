import api from "./api";

/**
 * Get fold metrics for a specific run and metric split
 * @param runId - The ID of the run
 * @param metricSplit - The metric split to retrieve (train, test, validation)
 * @returns Object with metrics data
 */
export const getFoldMetrics = async (
  runId: string,
  metricSplit: string,
): Promise<Record<string, number[]>> => {
  const response = await api.get<Record<string, number[]>>(
    `/v1/run/${runId}/fold-metrics`,
    {
      params: { metric_split: metricSplit },
    },
  );
  return response.data;
};

/**
 * Check if selected runs meet normality requirements for a given metric
 * @param metricName - The name of the metric to check
 * @param metricSplit - The metric split (train, test, validation)
 * @param runIds - Array of run IDs to check
 * @param foldMetrics - Object containing fold metrics for each run
 * @returns Object with is_normal boolean flag
 */
export const checkNormality = async (
  metricName: string,
  metricSplit: string,
  runIds: string[],
  foldMetrics: Record<string, number[]>,
): Promise<{ is_normal: boolean }> => {
  const response = await api.post<{ is_normal: boolean }>(
    "/v1/statistical-tests/normality-check",
    {
      metric_name: metricName,
      metric_split: metricSplit,
      run_ids: runIds,
      fold_metrics: foldMetrics,
    },
  );
  return response.data;
};

/**
 * Run a statistical test on selected runs
 * @param testName - The name of the statistical test (e.g., paired_t_test, anova_test)
 * @param metricName - The name of the metric
 * @param metricSplit - The metric split (train, test, validation)
 * @param runIds - Array of run IDs to compare
 * @param foldMetrics - Object containing fold metrics for each run
 * @param alpha - Significance level (default 0.05)
 * @returns Test results
 */
export const runStatisticalTest = async (
  testName: string,
  metricName: string,
  metricSplit: string,
  runIds: string[],
  foldMetrics: Record<string, number[]>,
  alpha: number = 0.05,
): Promise<unknown> => {
  const response = await api.post<unknown>("/v1/statistical-tests/run", {
    test_name: testName,
    metric_name: metricName,
    metric_split: metricSplit,
    run_ids: runIds,
    fold_metrics: foldMetrics,
    alpha,
  });
  return response.data;
};
