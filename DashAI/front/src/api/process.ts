import api from "./api";
import type { IProcess } from "../types/process";

export const getProcessesBySessionId = async (
  sessionId: string,
): Promise<IProcess[]> => {
  const response = await api.get<IProcess[]>(
    `/v1/generative-process/session/${sessionId}`,
  );
  return response.data;
};

export const getProcessById = async (processId: string): Promise<IProcess> => {
  const response = await api.get<IProcess>(
    `/v1/generative-process/${processId}`,
  );
  return response.data;
};

export const deleteProcessById = async (processId: string): Promise<void> => {
  await api.delete(`/v1/generative-process/${processId}`);
};

export const postProcess = async (
  sessionId: number,
  input: Array<File | string>,
): Promise<IProcess> => {
  const formData = new FormData();
  formData.append("session_id", sessionId.toString());

  input.forEach((item, index) => {
    if (item instanceof File) {
      formData.append(`file_${index}`, item);
    } else if (typeof item === "string") {
      formData.append(`text_${index}`, item);
    } else {
      console.error("Unsupported input type:", typeof item);
    }
  });

  const response = await api.post<IProcess>(
    `/v1/generative-process/`,
    formData,
  );
  return response.data;
};
