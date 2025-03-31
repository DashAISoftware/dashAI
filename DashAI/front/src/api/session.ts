import api from "./api";
import type { ISession } from "../types/session";

export const getSessions = async (): Promise<ISession[]> => {
  const response = await api.get<ISession[]>("/v1/generative-session");
  return response.data;
};
