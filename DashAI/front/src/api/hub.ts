import api from "./api";

const hubEndpoint = "/v1/dataset-source";

export interface DatasetSourceInfo {
  name: string;
  type: string;
  display_name: string;
  description: string;
}

export interface DatasetEntry {
  id: string;
  name: string;
  description: string;
  tags: string[];
  size_bytes: number | null;
  row_count: number | null;
  url: string;
  source: string;
}

export interface DatasetPreview {
  sample: Record<string, unknown>[];
  inferred_types: Record<string, unknown>;
  preview_row_count: number;
}

export const getDatasetSources = async (): Promise<DatasetSourceInfo[]> => {
  const response = await api.get<DatasetSourceInfo[]>(`${hubEndpoint}/`);
  return response.data;
};

export const searchDatasets = async (
  sourceName: string,
  query: string,
  limit = 20,
): Promise<DatasetEntry[]> => {
  const response = await api.get<DatasetEntry[]>(
    `${hubEndpoint}/${sourceName}/search`,
    { params: { q: query, limit } },
  );
  return response.data;
};

export const getDownloadUrl = async (
  sourceName: string,
  datasetId: string,
): Promise<string> => {
  const encodedId = encodeURIComponent(datasetId);
  const response = await api.get<{ url: string }>(
    `${hubEndpoint}/${sourceName}/${encodedId}/download-url`,
  );
  return response.data.url;
};

export const previewHubDataset = async (
  sourceName: string,
  datasetId: string,
  nRows = 100,
): Promise<DatasetPreview> => {
  const encodedId = encodeURIComponent(datasetId);
  const response = await api.get<DatasetPreview>(
    `${hubEndpoint}/${sourceName}/${encodedId}/preview`,
    { params: { n_rows: nRows } },
  );
  return response.data;
};

export const importHubDataset = async (
  sourceName: string,
  datasetId: string,
  dashaiDatasetId: number,
  params: Record<string, unknown>,
): Promise<{ job_id: string; dataset_id: number }> => {
  const encodedId = encodeURIComponent(datasetId);
  const response = await api.post<{ job_id: string; dataset_id: number }>(
    `${hubEndpoint}/${sourceName}/${encodedId}/import`,
    { dataset_id: dashaiDatasetId, params },
  );
  return response.data;
};
