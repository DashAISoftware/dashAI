import api from "./api";
import type { IGenerativeTask } from "../types/generativeTask";
import type { ISession } from "../types/session";

export const getGenerativeTask = async (): Promise<IGenerativeTask[]> => {
  const response = await api.get<IGenerativeTask[]>("/v1/component/?select_types=GenerativeTask");
  return response.data;
};

export const getRelatedComponents = async (relatedComponent: string): Promise<IGenerativeTask[]> => {
  const response = await api.get<IGenerativeTask[]>(`/v1/component/?related_component=${encodeURIComponent(relatedComponent)}`);
  return response.data;
};

export const createGenerativeSession = async (sessionData: Omit<ISession, "id" | "created" | "last_modified">): Promise<ISession> => {
  const response = await api.post<ISession>("/v1/generative-session/", sessionData);
  return response.data;
};