export interface ISession {
  id: string;
  name: string;
  description: string;
  created: Date;
  last_modified: Date;
  task_name: string;
  display_name: string;
  model_name: string;
  parameters: object;
}

export interface ISessionParameterHistory {
  id: number;
  session_id: number;
  parameters: Record<string, any>;
  modified_at: string;
}
