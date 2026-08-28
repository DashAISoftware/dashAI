import type { IDataset } from "./dataset";
import type { IRun } from "./run";

export interface ISessionConverter {
  converter: string;
  params: Record<string, unknown>;
  columns: string[];
  target_column?: string | null;
}

export interface IModelSession {
  id: string;
  dataset: IDataset;
  task_name: string;
  input_columns: string;
  output_columns: string;
  splits: string;
  converters?: ISessionConverter[];
  converters_invalidated?: boolean;
  // 0=NOT_STARTED, 1=DELIVERED, 2=STARTED, 3=FINISHED, 4=ERROR
  preprocessing_status?: number;
  preprocessing_huey_id?: string | null;
  preprocessed_path?: string | null;
  evaluation_strategy?: string;
  step: string;
  created: Date;
  last_modified: Date;
  runs: IRun[];
}
