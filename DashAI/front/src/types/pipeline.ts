export interface IStep {
  id: string;
  type: string;
  label: string;
  config: Record<string, unknown>;
}

export interface IPipeline {
  id: string;
  name: string;
  description: string;
  created: Date;
  last_modified: Date;
  steps: IStep[];
  exploration?: Record<string, unknown> | string;
  train?: {
    info?: string;
    parameters?: Record<string, unknown>;
    metrics?: Record<string, unknown>;
    model_path?: string;
    input_columns?: string[];
    task?: string;
  };
  task_and_model?: {
    task?: string;
    model?: string;
    parameters?: Record<string, unknown>;
    model_path?: string;
    input_columns?: string[];
  };
  metrics_result?: {
    metric_names?: string[];
    results?: Record<string, unknown>;
  };
  split_data?: Record<string, unknown>;
  prediction?: string;
}
