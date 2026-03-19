import api from "./api";
import type { IExploration } from "../types/exploration";

const explorationEndpoint = "/v1/exploration";

export const getExplorations = async (
  skip: number | null = null,
  limit: number | null = null,
): Promise<IExploration[]> => {
  const rawparams = { skip, limit };
  const params = Object.fromEntries(
    Object.entries(rawparams).filter(([_, v]) => v !== null),
  );

  const response = await api.get<IExploration[]>(`${explorationEndpoint}/`, {
    params,
  });
  return response.data;
};

export const getExplorationsByDatasetId = async (
  datasetId: number,
  skip: number | null = null,
  limit: number | null = null,
): Promise<IExploration[]> => {
  const rawparams = { skip, limit };
  const params = Object.fromEntries(
    Object.entries(rawparams).filter(([_, v]) => v !== null),
  );

  const response = await api.get<IExploration[]>(
    `${explorationEndpoint}/dataset/${datasetId}/`,
    { params },
  );
  return response.data;
};

export const deleteExploration = async (
  explorationId: number,
): Promise<object> => {
  const response = await api.delete(`${explorationEndpoint}/${explorationId}/`);
  return response.data;
};
