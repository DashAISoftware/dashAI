import api from "./api";
import type { IGenerativeTask } from "../types/generativeTask";

export const getGenerativeTask = async (): Promise<IGenerativeTask[]> => {
  const response = await api.get<IGenerativeTask[]>("/v1/component/?select_types=GenerativeTask");
  return response.data;
};

export const getRelatedComponents = async (relatedComponent: string): Promise<IGenerativeTask[]> => {
  const response = await api.get<IGenerativeTask[]>(`/v1/component/?related_component=${encodeURIComponent(relatedComponent)}`);
  return response.data;
};