export interface PairwiseResult {
  run_1: number;
  run_2: number;
  p_value: number;
  significant: boolean;
}

export interface StatisticalTestResponse {
  test_name: string;
  statistic: number | null;
  p_value: number | null;
  significant: boolean;
  alpha: number;
  details: Record<string, unknown> | null;
  posthoc: PairwiseResult[] | null;
}
