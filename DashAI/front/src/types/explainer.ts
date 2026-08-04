export interface IExplainer {
  id: string;
  name: string;
  run_id: number;
  explainer_name: string;
  dataset_id: number;
  explanation_path: string;
  plot_path: string;
  parameters: object;
  fit_parameters: object;
  created: Date;
  status: number;
  story?: string | null;
  story_huey_id?: string | null;
  stories?: Record<string, string> | null;
}
