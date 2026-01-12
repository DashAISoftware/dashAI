import api from "./api";
import type { IExperiment } from "../types/experiment";

const endpointURL = "/v1/experiment";

export const getExperiments = async (): Promise<IExperiment[]> => {
  const response = await api.get<IExperiment[]>(endpointURL);
  return response.data;
};

export const getExperimentById = async (id: string): Promise<IExperiment> => {
  const response = await api.get<IExperiment>(`${endpointURL}/${id}`);
  return response.data;
};

export const createExperiment = async (
  datasetId: number,
  taskName: string,
  expName: string,
  inputColumns: string[],
  outputColumns: string[],
  trainMetrics: string[],
  validationMetrics: string[],
  testMetrics: string[],
  splitsValue: JSON,
): Promise<IExperiment> => {
  const data = {
    dataset_id: datasetId,
    task_name: taskName,
    name: expName,
    input_columns: inputColumns,
    output_columns: outputColumns,
    train_metrics: trainMetrics,
    validation_metrics: validationMetrics,
    test_metrics: testMetrics,
    splits: splitsValue,
  };

  const response = await api.post<IExperiment>("/v1/experiment/", data);
  return response.data;
};

export const updateExperiment = async ({
  id,
  formData,
}: {
  id: string;
  formData: { name?: string; dataset_id?: number; task_name?: string };
}): Promise<object> => {
  const response = await api.patch(`/v1/experiment/${id}`, null, {
    params: formData,
  });
  return response.data;
};

export const deleteExperiment = async (id: string): Promise<object> => {
  const response = await api.delete(`/v1/experiment/${id}`);
  return response.data;
};

export const validateColumns = async (
  taskName: string,
  datasetId: number,
  inputColumns: string[],
  outputColumns: string[],
): Promise<object> => {
  const formData = {
    task_name: taskName,
    dataset_id: datasetId,
    inputs_columns: inputColumns,
    outputs_columns: outputColumns,
  };
  const response = await api.post<object>(
    "/v1/experiment/validation",
    formData,
  );
  return response.data;
};
