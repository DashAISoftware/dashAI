import api from "./api";

import type { IDataset } from "../types/dataset";
import { IParamsFilter } from "../types/predict";
const predictEndpoint = "/v1/predict";

export const get_prediction_table = async (): Promise<object> => {
  const response = await api.get(`${predictEndpoint}/prediction_table/`);
  return response.data;
};

export const get_model_table = async (): Promise<object> => {
  const response = await api.get(`${predictEndpoint}/model_table/`);
  return response.data;
};

export const get_metadata_prediction_json = async (): Promise<object> => {
  const response = await api.get(`${predictEndpoint}/metadata_json/`);
  return response.data;
};

export const delete_prediction = async (
  predict_name: string,
): Promise<object> => {
  const response = await api.delete(`${predictEndpoint}/${predict_name}`);
  return response.data;
};

export const rename_prediction = async (
  predict_name: string,
  new_name: string,
): Promise<object> => {
  const response = await api.patch(`${predictEndpoint}/${predict_name}/`, {
    new_name,
  });
  return response.data;
};

export const filter_datasets = async (requestData: IParamsFilter) => {
  const response = await api.post(
    `${predictEndpoint}/filter_datasets/`,
    requestData,
  );
  return response.data;
};

export const get_predict_summary = async (predictionId: string) => {
  const response = await api.get(`${predictEndpoint}/predict_summary`, {
    params: {
      pred_name: predictionId,
    },
  });
  return response.data;
};

export const download_predict = async (predict_name: string) => {
  const response = await api.get(`${predictEndpoint}/download/${predict_name}`);
  return response.data;
};
