import api from "./api";

const datasetExportEndpoint = "/v1/dataset-export";

export type CompatibilityStatus = "compatible" | "warning" | "incompatible";

export interface DatasetCompatibility {
  status: CompatibilityStatus;
  messages: string[];
  unsupported_columns: string[];
}

export interface ExportableDataset {
  id: number;
  name: string;
  total_rows: number | null;
  total_columns: number | null;
  compatibility: DatasetCompatibility;
}

export const getExportableDatasets = async (
  exporterName: string,
): Promise<ExportableDataset[]> => {
  const response = await api.get<ExportableDataset[]>(
    `${datasetExportEndpoint}/${exporterName}/datasets`,
  );
  return response.data;
};
