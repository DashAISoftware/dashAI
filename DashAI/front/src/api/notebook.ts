import api from "./api";
import type { INotebook } from "../types/notebook";

const notebookEndpoint = "/v1/notebook";

export const createNotebook = async (data: INotebook) => {
  const response = await api.post(notebookEndpoint, data);
  return response.data;
};

export const getNotebooks = async (): Promise<INotebook[]> => {
  const response = await api.get<INotebook[]>(notebookEndpoint);
  return response.data;
};
