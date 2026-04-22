import api from "./api";
import { IConverter } from "../types/converter";

const converterEndpoint = "/v1/converter";

export const saveConverter = async (
  converters: object,
): Promise<IConverter> => {
  const data = converters;

  const response = await api.post<IConverter>(`${converterEndpoint}`, data);
  return response.data;
};

export const getDatasetConverter = async (
  datasetId: number,
): Promise<IConverter> => {
  const response = await api.get<IConverter>(
    `${converterEndpoint}/${datasetId}`,
  );
  return response.data;
};

export const getConvertersByNotebook = async (
  notebookId: number,
): Promise<IConverter[]> => {
  const response = await api.get<IConverter[]>(
    `${converterEndpoint}/notebook/${notebookId}`,
  );
  return response.data;
};

export const getConverterById = async (id: number): Promise<IConverter> => {
  const response = await api.get<IConverter>(`${converterEndpoint}/${id}`);
  return response.data;
};

export const deleteConverterById = async (
  id: number,
): Promise<string | null> => {
  const response = await api.delete<{ jobId: string | null }>(
    `${converterEndpoint}/${id}`,
  );
  return response.data.jobId;
};
