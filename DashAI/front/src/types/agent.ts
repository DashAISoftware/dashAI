export interface IAgent {
  id: string;
  name: string;
  created: Date;
  description: string;
  last_modified: Date;
}


export interface IAgenticProcess {
  id: number;
  start_time: Date | null;
  status: number;
  conversation_id: number;
  end_time: Date | null;
  input: IAgenticConversationMessage[];
  output: IAgenticConversationMessage[];
}

export interface IAgenticConversationMessage {
  id: number;
  process_id: number;
  text: string;
  is_input: boolean;
}

export interface IAgentConfigurationParams {
  configuration_name: string;
  configuration_description: string;
  family_model_name: string;
  model_name: string;
  parameters: Record<string, unknown>;
  tools: string[];
}

export interface IAgentConfigurationSummary {
  id: number;
  created: Date;
  name: string;
  description: string | null;
  last_modified: Date;
}

export interface IAgentConfigurationUpdateParams {
  configuration_name?: string;
  configuration_description?: string;
  family_model_name?: string;
  model_name?: string;
  parameters?: Record<string, unknown>;
  tools?: string[];
}

export interface IAgentConfigurationDetail {
  id: number;
  created: Date;
  last_modified: Date;
  configuration_name: string;
  configuration_description: string | null;
  family_model_name: string;
  model_name: string;
  parameters: Record<string, unknown>;
  tools: string[];
}

