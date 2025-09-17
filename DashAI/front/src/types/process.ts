export interface IProcess {
  id: string;
  created: Date;
  last_modified: Date;
  start_time: Date | null;
  status: number;
  session_id: number;
  delivery_time: Date;
  end_time: Date | null;
  input: IDataProcess[];
  output: IDataProcess[];
}

export interface IDataProcess {
  id: number;
  process_id: number;
  data: string;
  data_type: string;
  is_input: boolean;
}
