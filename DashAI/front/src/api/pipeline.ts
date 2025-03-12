import api from "./api";
import type { IPipeline } from "../types/pipeline";

const pipelineEndpoint = "/v1/pipelines";

export const createPipeline = async (formData: object): Promise<IPipeline> => {
  const response = await api.post<IPipeline>(pipelineEndpoint, formData);
  return response.data;
};

export const getPipelines = async (): Promise<IPipeline[]> => {
  const response = await api.get<IPipeline[]>(pipelineEndpoint);
  return response.data;
};

export const getPipelineById = async (id: number): Promise<IPipeline> => {
  const response = await api.get<IPipeline>(`${pipelineEndpoint}/${id}`);
  return response.data;
};

export const updatePipeline = async (
  id: number,
  formData: object
): Promise<IPipeline> => {
  const response = await api.patch<IPipeline>(`${pipelineEndpoint}/${id}`, formData);
  return response.data;
};

export const deletePipeline = async (id: number): Promise<object> => {
  const response = await api.delete<object>(`${pipelineEndpoint}/${id}`);
  return response.data;
};
