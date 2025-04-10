import api from "./api";
import type { IRun } from "../types/run";

export const getRuns = async (experimentId: string = ""): Promise<IRun[]> => {
  const params = experimentId !== "" ? { experiment_id: experimentId } : {};
  const response = await api.get<IRun[]>("/v1/run/", { params });
  return response.data;
};

export const getRunById = async (runId: string): Promise<IRun> => {
  const response = await api.get<IRun>(`/v1/run/${runId}`);
  return response.data;
};

export const getHyperparameterPlot = async (
  runId: string,
  plotType: string,
): Promise<IRun> => {
  const response = await api.get<IRun>(`/v1/run/plot/${runId}/${plotType}`);
  return response.data;
};

export const createRun = async (
  experimentId: string,
  modelName: string,
  name: string,
  parameters: object,
  optimizerName: string,
  optimizerParameters: object,
  plotHistoryPath: string,
  plotSlicePath: string,
  plotContourPath: string,
  plotImportancePath: string,
  goalMetric: string,
  description: string,
): Promise<IRun> => {
  const data = {
    experiment_id: experimentId,
    model_name: modelName,
    name,
    parameters,
    optimizer_name: optimizerName,
    optimizer_parameters: optimizerParameters,
    plot_history_path: plotHistoryPath,
    plot_slice_path: plotSlicePath,
    plot_contour_path: plotContourPath,
    plot_importance_path: plotImportancePath,
    goal_metric: goalMetric,
    description,
  };

  const response = await api.post<IRun>("/v1/run/", data);
  return response.data;
};
