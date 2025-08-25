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
}
