import api from "./api";
import type { IProfileUpdate, IRegisterParams, IUser } from "../types/auth";

// The session lives in an httpOnly cookie set by the backend, so these calls
// never see or store a token

export const register = async (params: IRegisterParams): Promise<IUser> => {
  const response = await api.post<IUser>("/v1/auth/register", params);
  return response.data;
};

export const login = async (
  identifier: string,
  password: string,
): Promise<IUser> => {
  const response = await api.post<IUser>("/v1/auth/login", {
    identifier,
    password,
  });
  return response.data;
};

export const logout = async (): Promise<void> => {
  await api.post("/v1/auth/logout");
};

export const logoutAll = async (): Promise<void> => {
  await api.post("/v1/auth/logout-all");
};

export const getMe = async (): Promise<IUser> => {
  const response = await api.get<IUser>("/v1/auth/me");
  return response.data;
};

export const updateMe = async (changes: IProfileUpdate): Promise<IUser> => {
  const response = await api.patch<IUser>("/v1/auth/me", changes);
  return response.data;
};

export const changePassword = async (
  currentPassword: string,
  newPassword: string,
): Promise<void> => {
  await api.post("/v1/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
};
