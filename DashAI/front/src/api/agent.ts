import api from "./api";

import type {
  IAgent,
  IAgenticProcess,
  IAgentConfigurationParams,
  IAgentConfigurationSummary,
  IAgentConfigurationUpdateParams,
  IAgentConfigurationDetail,
} from "../types/agent";

const agentEndpoint = "/v1/agent";


export const fetchConversations = async (): Promise<IAgent[]> => {
  const response = await api.get<IAgent[]>(`${agentEndpoint}/`);
  return response.data;
};

export const fetchMessages = async (
  conversationId: number,
): Promise<IAgenticProcess[]> => {
  const response = await api.get<IAgenticProcess[]>(
    `${agentEndpoint}/conversation/${conversationId}/`,
  );
  return response.data;
};


export const getProcessById = async (
  processId: number,
): Promise<IAgenticProcess> => {
  const response = await api.get<IAgenticProcess>(
    `${agentEndpoint}/${processId}`,
  );
  return response.data;
};

export const deleteProcessById = async (processId: number): Promise<void> => {
  await api.delete(`${agentEndpoint}/${processId}`);
};


export const createConversation = async (name: string): Promise<IAgent> => {
  const response = await api.post<IAgent>(`${agentEndpoint}/`, {
    name: name,
    description: "",
  });
  return response.data;
};

export const updateConversationTitle = async (
  id: number,
  newTitle: string,
): Promise<void> => {
  const response = await api.patch(`${agentEndpoint}/${id}/`, {
    name: newTitle,
  });
  return response.data;
};

export const deleteConversation = async (
  conversationId: number,
): Promise<object> => {
  const response = await api.delete(`${agentEndpoint}/${conversationId}/`);
  return response;
};

export const postProcess = async (
  conversationId: number,
  configurationId: number,
  input: string,
): Promise<IAgenticProcess> => {

  const formData = new FormData();
  formData.append("conversation_id", conversationId.toString());
  formData.append("configuration_id", configurationId.toString());
  formData.append("input_data", input);

  const response = await api.post<IAgenticProcess>(
    `${agentEndpoint}/process/`,
    formData,
  );
  return response.data;
};


export const enqueueAgenticProcessJob = async (
  processId: number,
  configurationId: number,
): Promise<object> => {
  const response = await api.post<object>("/v1/job/agentic/", {
    agentic_process_id: processId,
    configuration_id: configurationId,
  });
  return response.data;
};

export const fetchDefaultAgentParameters = async (): Promise<object[]> => {
  const response = await api.get<object[]>("/v1/component/", {
    params: {
      related_component: "AgentTask",
    }
  });
  return response.data;
};
export const createAgentConfiguration = async (
  params: IAgentConfigurationParams,
): Promise<object> => {
  const response = await api.post<object>(`${agentEndpoint}/configuration/`, params);
  return response.data;
};

export const fetchAgentConfigurations = async (): Promise<
  IAgentConfigurationSummary[]
> => {
  const response = await api.get<IAgentConfigurationSummary[]>(
    `${agentEndpoint}/configuration/`,
  );
  return response.data;
};

export const fetchAgentConfigurationById = async (
  configurationId: number,
): Promise<IAgentConfigurationDetail> => {
  const response = await api.get<IAgentConfigurationDetail>(
    `${agentEndpoint}/configuration/${configurationId}`,
  );
  return response.data;
};

export const updateAgentConfiguration = async (
  configurationId: number,
  params: IAgentConfigurationUpdateParams,
): Promise<object> => {
  const response = await api.patch<object>(
    `${agentEndpoint}/configuration/${configurationId}`,
    params,
  );
  return response.data;
};

export const deleteAgentConfiguration = async (
  configurationId: number,
): Promise<void> => {
  await api.delete(`${agentEndpoint}/configuration/${configurationId}`);
};