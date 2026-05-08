import api from "./api";

const hubEndpoint = "/v1/dataset-source";

export interface DatasetSourceInfo {
  name: string;
  type: string;
  display_name: string;
  description: string;
  compatible_components: string[];
}

export interface ComponentInfo {
  name: string;
  display_name: string;
  description: string;
  schema: Record<string, unknown>;
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
  offset = 0,
): Promise<DatasetEntry[]> => {
  const response = await api.get<DatasetEntry[]>(
    `${hubEndpoint}/${sourceName}/search`,
    { params: { q: query, limit, offset } },
  );
  return response.data;
};

export const getDatasetInfo = async (
  sourceName: string,
  datasetId: string,
): Promise<{ id?: string; description?: string; tags?: string[] }> => {
  const encodedId = encodeURIComponent(datasetId);
  const response = await api.get<{
    id?: string;
    description?: string;
    tags?: string[];
  }>(`${hubEndpoint}/${sourceName}/${encodedId}/info`);
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
  dataloader?: string,
  params?: Record<string, unknown>,
): Promise<DatasetPreview> => {
  const encodedId = encodeURIComponent(datasetId);
  const response =
    dataloader || params
      ? await api.post<DatasetPreview>(
          `${hubEndpoint}/${sourceName}/${encodedId}/preview`,
          { dataloader, params: params ?? {}, n_rows: nRows },
        )
      : await api.get<DatasetPreview>(
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

export const getComponentInfo = async (
  componentName: string,
): Promise<ComponentInfo> => {
  const response = await api.get<ComponentInfo>(
    `/v1/component/${componentName}/`,
  );
  return response.data;
};

// ---- Hub Downloads ----

const hubDownloadEndpoint = "/v1/hub-download";

export type HubDownloadStatus = "downloading" | "ready" | "error";

export interface HubDownload {
  id: number;
  source_name: string;
  dataset_id: string;
  name: string;
  local_path: string | null;
  status: HubDownloadStatus;
  error_message: string | null;
  created: string | null;
  last_modified: string | null;
  job_id?: string;
}

export const listHubDownloads = async (): Promise<HubDownload[]> => {
  const response = await api.get<HubDownload[]>(`${hubDownloadEndpoint}/`);
  return response.data;
};

export const getHubDownload = async (id: number): Promise<HubDownload> => {
  const response = await api.get<HubDownload>(`${hubDownloadEndpoint}/${id}`);
  return response.data;
};

export const createHubDownload = async (
  source_name: string,
  dataset_id: string,
  name: string,
): Promise<HubDownload> => {
  const response = await api.post<HubDownload>(`${hubDownloadEndpoint}/`, {
    source_name,
    dataset_id,
    name,
  });
  return response.data;
};

export const deleteHubDownload = async (id: number): Promise<void> => {
  await api.delete(`${hubDownloadEndpoint}/${id}`);
};

export const listHubDownloadFiles = async (id: number): Promise<string[]> => {
  const response = await api.get<string[]>(
    `${hubDownloadEndpoint}/${id}/files`,
  );
  return response.data;
};
