import api from "./api";
import { IConverter } from "../types/converter";

const converterEndpoint = "/v1/converter";

export const saveConverterList = async (
  converters: object,
): Promise<IConverter> => {
  const data = converters;

  const response = await api.post<IConverter>(`${converterEndpoint}`, data);
  return response.data;
};

export const getDatasetConverterList = async (
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
