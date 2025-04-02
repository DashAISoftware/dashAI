export interface ISession {
  id: string;
  name: string;
  description: string;
  created: Date;
  last_modified: Date;
  task_name: string;
  model_name: string;
  parameters: object;
}
