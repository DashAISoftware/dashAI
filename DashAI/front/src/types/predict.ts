export interface IPredict {
  model_session_id: number;
  model_session_name: string;
  created: string;
  run_name: string;
  model_name: string;
}

export interface IParamsFilter {
  run_id: number;
}
