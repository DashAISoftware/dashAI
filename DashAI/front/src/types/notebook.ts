export interface INotebook {
  id: string;
  dataset_id: string;
  created: Date;
  last_modified: Date;
  file_path: string;
  name: string;
  description: string;
}
