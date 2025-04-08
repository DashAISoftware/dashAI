export interface IProcess {
  id: string;
  created: Date;
  last_modified: Date;
  start_time: Date | null;
  input: string;
  status: number;
  session_id: number;
  delivery_time: Date;
  end_time: Date | null;
  output: any | null;
}
