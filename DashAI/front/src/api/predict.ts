import api from "./api";

import type { IDataset } from "../types/dataset";
import { IParamsFilter } from "../types/predict";
const predictEndpoint = "/v1/predict";

export const filterDatasets = async (requestData: IParamsFilter) => {
  const response = await api.get(`${predictEndpoint}/filter_datasets`, {
    params: requestData,
  });
  return response.data;
};

export const downloadPredict = async (prediction_id: string) => {
  const response = await api.get(
    `${predictEndpoint}/download/${prediction_id}`,
  );
  return response.data;
};

export const createPrediction = async (
  run_id: number,
  dataset_id?: number,
): Promise<object> => {
  const response = await api.post<object>(`${predictEndpoint}/`, {
    run_id,
    dataset_id,
  });
  return response.data;
};

export const getPredictions = async (
  run_id?: number,
  prediction_id?: string,
): Promise<object[]> => {
  const response = await api.get<object[]>(`${predictEndpoint}/`, {
    params: {
      run_id,
      prediction_id,
    },
  });
  return response.data;
};

export const getPredictionSummary = async (
  prediction_id: string,
): Promise<object[]> => {
  const response = await api.get<object[]>(`${predictEndpoint}/summary/`, {
    params: {
      prediction_id,
    },
  });
  return response.data;
};

export const deletePrediction = async (
  prediction_id: string,
): Promise<void> => {
  await api.delete(`${predictEndpoint}/${prediction_id}`);
};
