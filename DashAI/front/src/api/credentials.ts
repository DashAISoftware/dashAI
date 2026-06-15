import api from "./api";
import { getComponents } from "./component";
import type { ICredential } from "../types/credential";

interface ICredentialStatus {
  name: string;
  is_authenticated: boolean;
  key: string | null;
}

export const getCredentialStatus = async (
  name: string,
): Promise<ICredentialStatus> => {
  const response = await api.get<ICredentialStatus>(`/v1/credential/${name}`);
  return response.data;
};

// The catalog of credential components (name, display name, description) comes
// from the components endpoint; per-credential auth state comes from the
// credential endpoint. They are merged here so the modal renders any
// backend-registered credential without frontend changes.
export const getCredentials = async (): Promise<ICredential[]> => {
  const components = await getComponents({ selectTypes: ["Credential"] });
  return Promise.all(
    components.map(async (component) => {
      const status = await getCredentialStatus(component.name);
      return {
        name: component.name,
        display_name: component.display_name ?? component.name,
        description: component.description ?? "",
        is_authenticated: status.is_authenticated,
        key: status.key,
      };
    }),
  );
};

export const authenticateCredential = async (
  name: string,
  key: string,
): Promise<{ is_authenticated: boolean }> => {
  const response = await api.post<{ is_authenticated: boolean }>(
    `/v1/credential/${name}/auth`,
    { key },
  );
  return response.data;
};

export const deleteCredential = async (
  name: string,
): Promise<{ is_authenticated: boolean }> => {
  const response = await api.delete<{ is_authenticated: boolean }>(
    `/v1/credential/${name}`,
  );
  return response.data;
};
