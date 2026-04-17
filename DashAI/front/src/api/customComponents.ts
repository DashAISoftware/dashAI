import api from "./api";
import type {
  BaseClassInfo,
  BaseClassSummary,
  ComponentSource,
  CustomComponent,
  CustomComponentCreate,
  CustomComponentUpdate,
  ValidationRequest,
  ValidationResponse,
} from "../types/customComponent";

const BASE = "/v1/custom-component";

export const listBaseClasses = async (): Promise<BaseClassSummary[]> => {
  const response = await api.get<BaseClassSummary[]>(`${BASE}/base-classes`);
  return response.data;
};

export const getBaseClassInfo = async (
  name: string,
): Promise<BaseClassInfo> => {
  const response = await api.get<BaseClassInfo>(`${BASE}/base-classes/${name}`);
  return response.data;
};

export const validateCustomComponent = async (
  body: ValidationRequest,
): Promise<ValidationResponse> => {
  const response = await api.post<ValidationResponse>(`${BASE}/validate`, body);
  return response.data;
};

export const listCustomComponents = async (): Promise<CustomComponent[]> => {
  const response = await api.get<CustomComponent[]>(`${BASE}/`);
  return response.data;
};

export const getCustomComponent = async (
  id: number,
): Promise<CustomComponent> => {
  const response = await api.get<CustomComponent>(`${BASE}/${id}`);
  return response.data;
};

export const createCustomComponent = async (
  body: CustomComponentCreate,
): Promise<CustomComponent> => {
  const response = await api.post<CustomComponent>(`${BASE}/`, body);
  return response.data;
};

export const updateCustomComponent = async (
  id: number,
  body: CustomComponentUpdate,
): Promise<CustomComponent> => {
  const response = await api.put<CustomComponent>(`${BASE}/${id}`, body);
  return response.data;
};

export const deleteCustomComponent = async (id: number): Promise<void> => {
  await api.delete(`${BASE}/${id}`);
};

export const getComponentSource = async (
  className: string,
): Promise<ComponentSource> => {
  const response = await api.get<ComponentSource>(
    `${BASE}/source/${className}`,
  );
  return response.data;
};
