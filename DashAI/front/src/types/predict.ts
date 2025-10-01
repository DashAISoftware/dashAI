export interface IPredict {
  experiment_id: number;
  experiment_name: string;
  created: string;
  run_name: string;
  model_name: string;
}

export interface IParamsFilter {
  run_id: number;
}
