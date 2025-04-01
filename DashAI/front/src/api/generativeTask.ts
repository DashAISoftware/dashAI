import api from "./api";
import type { IGenerativeTask } from "../types/generativeTask";

export const getGenerativeTask = async (): Promise<IGenerativeTask[]> => {
  const response = await api.get<IGenerativeTask[]>("/v1/task/get-all");
  return response.data;
};