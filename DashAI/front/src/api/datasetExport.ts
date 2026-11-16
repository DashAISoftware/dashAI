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

export type DatasetExportStatus =
  "pending" | "preparing" | "uploading" | "published" | "error";

export interface DatasetExport {
  id: number;
  dataset_id: number | null;
  dataset_name: string;
  exporter_name: string;
  params: Record<string, unknown>;
  status: DatasetExportStatus;
  remote_id: string | null;
  remote_url: string | null;
  error_message: string | null;
  huey_id: string | null;
  created: string | null;
  last_modified: string | null;
}

export const getExport = async (exportId: number): Promise<DatasetExport> => {
  const response = await api.get<DatasetExport>(
    `${datasetExportEndpoint}/${exportId}`,
  );
  return response.data;
};

export const listExports = async (
  datasetId?: number,
): Promise<DatasetExport[]> => {
  const response = await api.get<DatasetExport[]>(`${datasetExportEndpoint}/`, {
    params: datasetId === undefined ? {} : { dataset_id: datasetId },
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
