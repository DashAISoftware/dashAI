import api from "./api";
import type { IComponent } from "../types/component";

interface componentQuery {
  model?: string;
  selectTypes?: string[];
  ignoreTypes?: string[];
  relatedComponent?: string;
  componentParent?: string;
  hasRelatedOfType?: string;
}

export const getComponents = async ({
  model = "",
  selectTypes = [],
  ignoreTypes = [],
  relatedComponent = "",
  hasRelatedOfType = "",
  componentParent = "",
}: componentQuery = {}): Promise<IComponent[]> => {
  let params = {};

  if (selectTypes.length > 0) {
    params = { ...params, select_types: selectTypes };
  }

  if (ignoreTypes.length > 0) {
    params = { ...params, ignore_types: ignoreTypes };
  }

  if (relatedComponent !== "") {
    params = { ...params, related_component: relatedComponent };
  }

  if (componentParent !== "") {
    params = { ...params, component_parent: componentParent };
  }

  if (hasRelatedOfType !== "") {
    params = { ...params, has_related_of_type: hasRelatedOfType };
  }

  const url = model ? `/v1/component/${model}/` : `/v1/component/`;
  const response = await api.get<IComponent[]>(url, {
    params,
    paramsSerializer: {
      indexes: null, // brackets don't appear in the url
    },
  });
  return response.data;
};

export const getChildComponents = async (
  componentName: string,
  recursive: boolean,
): Promise<IComponent[]> => {
  const response = await api.get<IComponent[]>(
    `/v1/component/${componentName}/children`,
    {
      params: { recursive },
    },
  );
  return response.data;
};
export const getComponentById = async (id: string): Promise<IComponent> => {
  const response = await api.get<IComponent>(`/v1/component/${id}/`);
  return response.data;
};
