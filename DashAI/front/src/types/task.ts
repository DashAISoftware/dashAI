export interface ITask {
  class: string;
  name: string;
  help: string;
  description: string;
  type: string;
}
// One role a task's columns can play, as the task's metadata lists it.
export interface ITaskColumnRole {
  name: string;
  label: string;
  types: string[];
  min: number;
  max: "n" | number;
  required: boolean;
  transformable: boolean;
}

export interface ITaskMetadataParameters {
  column_roles?: ITaskColumnRole[];
  // Which roles feed a model's inputs and which its outputs.
  io_roles?: { inputs: string[]; outputs: string[] };
  // How a trained model is asked for predictions: the rows of a dataset, or
  // a number of steps past the end of its training series.
  prediction_mode?: "rows" | "horizon";
  requires_target?: boolean;
  // Whether a session may preprocess the task's columns.
  takes_preprocessing?: boolean;
  // A Material UI icon name, as a model declares its own.
  icon?: string;
  requires_download?: boolean;
  download_size_bytes?: number | null;
}

// What an evaluation strategy declares in its metadata.
export interface IEvaluationStrategyMetadata {
  kind: string;
  scored_splits: string[];
  // The partitioning of the splitters it takes, or null when it takes none.
  splitter_partitioning: string | null;
  // The splitter a session starts on, or null for the first one offered.
  default_splitter: string | null;
  // The views of a finished run beyond its metrics.
  result_views: ("fold_metrics" | "forecasts")[];
}
