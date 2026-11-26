import api from "./api";

const endpointURL = "/v1/loaded-models";

export interface LoadedModel {
  id: number;
  slot: string;
  label: string;
  load_params: Record<string, unknown> | null;
  ram_bytes: number | null;
  gpu_bytes: number | null;
  loaded_at: string;
  last_used_at: string;
  in_use: boolean;
  unload_requested: boolean;
}

export const getLoadedModels = async (): Promise<LoadedModel[]> => {
  const response = await api.get<LoadedModel[]>(`${endpointURL}/`);
  return response.data;
};

export const unloadModel = async (id: number): Promise<void> => {
  await api.post(`${endpointURL}/${id}/unload`);
};
