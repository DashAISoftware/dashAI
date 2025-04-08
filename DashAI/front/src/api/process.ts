import api from "./api";
import type { IProcess } from "../types/process";

export const getProcesses = async (sessionId: string): Promise<IProcess[]> => {
  const response = await api.get<IProcess[]>(
    `/v1/generative-process/${sessionId}`,
  );
  return response.data;
};
