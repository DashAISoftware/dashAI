export interface PairwiseResult {
  run_1: number;
  run_2: number;
  p_value: number;
  significant: boolean;
}

export interface NormalityTestResult {
  run_id: number;
  p_value: number;
  is_normal: boolean;
}

export interface NormalityCheckResponse {
  is_normal: boolean;
  results_by_run: NormalityTestResult[];
  test_used: string;
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
