import api from "./api";
import type { IDataset, DatasetPage } from "../types/dataset";

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

export const getExperimentsExist = async (id: number): Promise<object> => {
  const response = await api.get<object>(
    `${datasetEndpoint}/${id}/experiments-exist`,
  );
  return response.data;
};

export const updateDataset = async (
  id: number,
  formData: object,
): Promise<IDataset> => {
  const response = await api.patch(`${datasetEndpoint}/${id}`, { ...formData });
  return response.data;
};

export const deleteDataset = async (id: string): Promise<object> => {
  const response = await api.delete(`${datasetEndpoint}/${id}`);
  return response.data;
};

export const getDatasetFile = async (path: string, page = 0, pageSize = 5) => {
  const response = await api.get(`${datasetEndpoint}/file/`, {
    params: { path, page, page_size: pageSize },
  });
  return response.data;
};
