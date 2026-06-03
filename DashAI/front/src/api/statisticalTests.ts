import api from "./api";

import { StatisticalTestResponse } from "../types/statisticalTests";

/**
 * Get fold metrics for a specific run and metric split.
 */
export const getFoldMetrics = async (
  runId: string,
  metricSplit: string,
  level: "fold" | "outer" = "fold",
): Promise<Record<string, number[]>> => {
  const response =
    level === "fold"
      ? await api.get<Record<string, number[]>>(
          `/v1/run/${runId}/fold-metrics`,
          { params: { metric_split: metricSplit } },
        )
      : await api.get<Record<string, number[]>>(
          `/v1/run/${runId}/outer-fold-metrics`,
          { params: { metric_split: metricSplit } },
        );
  return response.data;
};

/**
 * Run a statistical test on selected runs.
 * Automatically includes post-hoc results when applicable
 * (Nemenyi after significant Friedman, Tukey after significant ANOVA).
 *
 * @param params - Extra test-specific params (e.g. { alternative: "two-sided" })
 */
export const runStatisticalTest = async (
  testName: string,
  metricName: string,
  metricSplit: string,
  runIds: number[],
  runNames: Record<string, string>,
  foldMetrics: Record<string, number[]>,
  alpha: number = 0.05,
  params: Record<string, unknown> = {},
): Promise<StatisticalTestResponse> => {
  const response = await api.post<StatisticalTestResponse>(
    "/v1/statistical-tests/run",
    {
      test_name: testName,
      metric_name: metricName,
      metric_split: metricSplit,
      run_ids: runIds,
      run_names: runNames,
      fold_metrics: foldMetrics,
      alpha,
      params,
    },
  );
  return response.data;
};
