export interface IGenerativeTask {
  name: string;
  type: string;
  configurable_object: boolean;
  schema: any | null;
  metadata: {
    inputs_types: string[];
    outputs_types: string[];
    inputs_cardinality: number;
    outputs_cardinality: number;
  };
  description: string;
  display_name: string;
  color: string | null;
}
