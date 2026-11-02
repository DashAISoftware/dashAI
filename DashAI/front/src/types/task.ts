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
  inputs_columns: string[];
  outputs_columns: string[];
  inputs_cardinality: "n" | number;
  outputs_cardinality: "n" | number;
  requires_download?: boolean;
  download_size_bytes?: number | null;
}
