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

export interface CreatedExport {
  export_id: number;
  job_id: string;
}

export interface ExportValidation {
  errors: string[];
  warnings: string[];
}

export const validateExport = async (
  exporterName: string,
  datasetId: number,
  params: Record<string, unknown>,
): Promise<ExportValidation> => {
  const response = await api.post<ExportValidation>(
    `${datasetExportEndpoint}/${exporterName}/validate`,
    { dataset_id: datasetId, params },
  );
  return response.data;
};

export const createExport = async (
  exporterName: string,
  datasetId: number,
  params: Record<string, unknown>,
): Promise<CreatedExport> => {
  const response = await api.post<CreatedExport>(`${datasetExportEndpoint}/`, {
    dataset_id: datasetId,
    exporter_name: exporterName,
    params,
  });
  return response.data;
};

export const getExportableDatasets = async (
  exporterName: string,
): Promise<ExportableDataset[]> => {
  const response = await api.get<ExportableDataset[]>(
    `${datasetExportEndpoint}/${exporterName}/datasets`,
  );
  return response.data;
};
