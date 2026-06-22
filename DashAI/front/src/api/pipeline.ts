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

export const getNodes = async () => {
  const response = await api.get(`${pipelineEndpoint}/nodes`);
  return response.data;
};

export const getNodeContracts = async () => {
  const response = await api.get(`${pipelineEndpoint}/contracts`);
  return response.data;
};

export const updatePipeline = async (
  id: number,
  formData: object,
): Promise<IPipeline> => {
  const response = await api.put<IPipeline>(
    `${pipelineEndpoint}/${id}`,
    formData,
  );
  return response.data;
};

export const deletePipeline = async (id: number): Promise<object> => {
  const response = await api.delete<object>(`${pipelineEndpoint}/${id}`);
  return response.data;
};

export const validateNode = async (
  nodeType: string,
  config: object,
): Promise<{ status: string; message?: string }> => {
  const response = await api.post(`${pipelineEndpoint}/validate_node`, {
    type: nodeType,
    config: config,
  });
  return response.data;
};

export const validatePipeline = async (
  nodes: Array<object>,
  edges: Array<object>,
): Promise<{ errors?: Record<string, string[]> }> => {
  const response = await api.post(`${pipelineEndpoint}/validate_pipeline`, {
    nodes: nodes,
    edges: edges,
  });
  return response.data;
};

export const validateEdge = async (payload: object) => {
  const response = await api.post(`${pipelineEndpoint}/validate_edge`, payload);
  return response.data;
};

export const getPipelinePredictionSummary = async (predictionId: string) => {
  const response = await api.get(`${pipelineEndpoint}/predict_summary`, {
    params: {
      pred_name: predictionId,
    },
  });
  return response.data;
};

export const getExplorationResults = async (id: number) => {
  const response = await api.get(
    `${pipelineEndpoint}/${id}/dataexploration/results`,
  );
  return response.data;
};

export const filterModels = async (
  dataset_id: string,
  pipeline_id: number | null = null,
): Promise<IPipeline[]> => {
  const response = await api.post(`${pipelineEndpoint}/filter_models`, {
    dataset_id: dataset_id,
    pipeline_id: pipeline_id,
  });
  return response.data;
};
