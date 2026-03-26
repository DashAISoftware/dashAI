import api from "./api";

import { IParamsFilter } from "../types/predict";
const predictEndpoint = "/v1/predict";

export const filterDatasets = async (requestData: IParamsFilter) => {
  const response = await api.get(`${predictEndpoint}/filter_datasets`, {
    params: requestData,
  });
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

export const deletePrediction = async (
  prediction_id: string,
): Promise<void> => {
  await api.delete(`${predictEndpoint}/${prediction_id}`);
};

export const previewManualPrediction = async (
  runId: number,
  manualInputData: Record<string, unknown>[],
): Promise<{ columns: string[]; rows: unknown[][] }> => {
  const formData = new FormData();

  const simpleData = manualInputData.map((obj, i) => {
    const cleanObj: Record<string, unknown> = {};
    Object.entries(obj).forEach(([key, value]) => {
      if (value instanceof File) {
        const fileFieldKey = `file_${i}_${key}`;
        formData.append(fileFieldKey, value);
        cleanObj[key] = fileFieldKey;
      } else {
        cleanObj[key] = value;
      }
    });
    return cleanObj;
  });

  formData.append("run_id", String(runId));
  formData.append("manual_input_data", JSON.stringify(simpleData));

  const response = await api.post<{ columns: string[]; rows: unknown[][] }>(
    `${predictEndpoint}/preview`,
    formData,
  );
  return response.data;
};
