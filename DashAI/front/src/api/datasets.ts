import api from "./api";
import type { IDataset } from "../types/dataset";

const datasetEndpoint = "/v1/dataset";

export const copyDataset = async (formData: object): Promise<object> => {
  const response = await api.post<object>(`${datasetEndpoint}/copy`, formData);
  return response.data;
};

export const getDatasets = async (): Promise<IDataset[]> => {
  const response = await api.get<IDataset[]>(datasetEndpoint);
  return response.data;
};

export const getDatasetSample = async (id: number): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/${id}/sample`);
  return response.data;
};

export const getDatasetSampleByFilePath = async (
  path: string,
): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/sample/file`, {
    params: { path },
  });
  return response.data;
};

export const getDatasetTypes = async (id: number): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/${id}/types`);
  return response.data;
};

export const getDatasetTypesByFilePath = async (
  path: string,
): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/types/file`, {
    params: { path },
  });
  return response.data;
};

export const getDatasetInfo = async (id: number): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/${id}/info`);
  return response.data;
};

export const getDatasetInfoByFilePath = async (
  path: string,
): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/file/info`, {
    params: { path },
  });
  return response.data;
};

export const getExperimentsExist = async (id: number): Promise<object> => {
  const response = await api.get<object>(
    `${datasetEndpoint}/${id}/experiments-exist`,
  );
  return response.data;
};

export const createDataset = async (name: string): Promise<IDataset> => {
  const response = await api.post<IDataset>(`${datasetEndpoint}/`, {
    name: name,
  });
  return response.data;
};

export const updateDataset = async (
  id: number,
  formData: object,
): Promise<IDataset> => {
  const response = await api.patch<IDataset>(`${datasetEndpoint}/${id}`, {
    ...formData,
  });
  return response.data;
};

export const deleteDataset = async (id: string): Promise<object> => {
  const response = await api.delete(`${datasetEndpoint}/${id}`);
  return response.data;
};

export const getDatasetTemporalInfo = async (
  id: number,
  timestampColumn: string,
): Promise<{
  frequency_code: string;
  frequency_label: string;
  frequency_description: string;
  frequency_example: string;
  average_interval: string;
  start_date: string;
  end_date: string;
  total_periods: number;
  detected_gaps: number;
  timestamp_column: string;
}> => {
  const response = await api.get(`${datasetEndpoint}/${id}/temporal-info`, {
    params: { timestamp_column: timestampColumn },
  });
  return response.data;
};

export const getDatasetFile = async (path: string, page = 0, pageSize = 5) => {
  const response = await api.get(`${datasetEndpoint}/file/`, {
    params: { path, page, page_size: pageSize },
  });
  return response.data;
};

export const exportDatasetCsvById = async (id: number): Promise<Blob> => {
  const response = await api.get(`${datasetEndpoint}/${id}/export/csv`, {
    responseType: "blob",
  });
  return response.data;
};

export const exportDatasetCsvByPath = async (path: string): Promise<Blob> => {
  const response = await api.get(`${datasetEndpoint}/export/csv`, {
    params: { path },
    responseType: "blob",
  });
  return response.data;
};
