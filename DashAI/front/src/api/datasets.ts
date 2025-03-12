import api from "./api";
import type { IDataset } from "../types/dataset";

const datasetEndpoint = "/v1/dataset";

export const getDatasets = async (): Promise<IDataset[]> => {
  const response = await api.get<IDataset[]>(datasetEndpoint);
  return response.data;
};

export const getDatasetSample = async (id: number): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/${id}/sample`);
  return response.data;
};

export const getDatasetTypes = async (id: number): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/${id}/types`);
  return response.data;
};

export const getDatasetInfo = async (id: number): Promise<object> => {
  const response = await api.get<object>(`${datasetEndpoint}/${id}/info`);
  return response.data;
};

export const getImageColumnsInfo = async (id: number): Promise<object> => {
  const response = await api.get<object>(
    `${datasetEndpoint}/${id}/image_columns_info`,
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
