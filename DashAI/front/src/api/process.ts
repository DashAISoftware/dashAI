import api from "./api";
import type { IProcess } from "../types/process";

export const getProcesses = async (sessionId: string): Promise<IProcess[]> => {
  const response = await api.get<IProcess[]>(
    `/v1/generative-process/${sessionId}`,
  );
  return response.data;
};

export const postProcess = async (
  sessionId: number,
  input: string,
): Promise<IProcess> => {
  const data = {
    session_id: sessionId,
    input: input,
  };
  const response = await api.post<IProcess>(`/v1/generative-process/`, data, {
    headers: { "Content-Type": "application/json" },
  });
  return response.data;
};
