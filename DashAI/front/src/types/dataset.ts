export interface IDataset {
  id: string;
  name: string;
  created: Date;
  last_modified: Date;
  file_path: string;
}

export interface DatasetPage {
  rows: Record<string, any>[];
  total: number;
}
