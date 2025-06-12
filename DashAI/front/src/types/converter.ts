export interface IConverter {
  id: number;
  status: number;
  dataset_id: string;
  created: Date;
  converters: Object;
}

export enum ConverterListStatus {
  NOT_STARTED,
  DELIVERED,
  STARTED,
  FINISHED,
  ERROR,
}
