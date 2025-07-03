import api from "./api";
import { ISession } from "../types/session";
import { IGenerativeTask } from "../types/generativeTask";


// Fetch all RAG sessions
export const getRAGSessions = async (): Promise<ISession[]> => {

  const response = await api.get<ISession[]>("/v1/generative-session/");
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG sessions: ${response.statusText}`);
  }

  return response.data;
}

export const getRAGSession = async (sessionId: number): Promise<ISession> => {

  const response = await api.get<ISession>(`/v1/generative-session/${sessionId}`);
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG session: ${response.statusText}`);
  }

  return response.data;
}

export const createRAGSession = async (
  sessionData: Omit<ISession, "id" | "created" | "last_modified">
): Promise<ISession> => {
  console.log("Original RAG session input:", sessionData);

  const params = sessionData.parameters as {
  documents: string[];
  retriever_model: {
    name: string;
    parameters: Record<string, any>;
  };
  generator_model: {
    name: string;
    parameters: Record<string, any>;
  };
  };

  const transformedSession: Omit<ISession, "id" | "created" | "last_modified"> = {
    name: sessionData.name,
    description: sessionData.description,
    task_name: "RAGTask",
    model_name: "RAGPipeline",
    display_name: "",
    parameters: {
      documents: params.documents,
      retriever_model: {
        component: params.retriever_model.name,
        params: params.retriever_model.parameters,
      },
      generation_model: {
        component: params.generator_model.name,
        params: params.generator_model.parameters,
      },
    },
  };


  
  console.log("Sending RAG session as:", transformedSession);

  const response = await api.post<ISession>("/v1/generative-session/", transformedSession);

  if (response.status !== 201) {
    throw new Error(`Failed to create RAG session: ${response.statusText}`);
  }

  console.log("RAG session created successfully:", response.data);
  return response.data;
};

export const updateRAGSession = async (sessionId: number, sessionData: Partial<ISession>): Promise<ISession> => {

  const response = await api.put<ISession>(`/v1/generative-session/${sessionId}`, sessionData);
  if (response.status !== 200) {
    throw new Error(`Failed to update RAG session: ${response.statusText}`);
  }

  return response.data;
}

export const deleteRAGSession = async (sessionId: number): Promise<void> => {
  const response = await api.delete(`/v1/generative-session/${sessionId}`);
  if (response.status !== 204) {
    throw new Error(`Failed to delete RAG session: ${response.statusText}`);
  }

}

export const updateGenerativeSessionParams = async (
  sessionId: number,
  newParams: Record<string, any>,
): Promise<ISession> => {

  const response = await api.put<ISession>(
    `/v1/generative-session/${sessionId}/parameters`,
    newParams,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to update RAG session parameters: ${response.statusText}`);
  }
  return response.data;
}


export const getRetrieverComponents = async (): Promise<IGenerativeTask[]> => {

  const response = await api.get(
    `/v1/component/?select_types=RetrieverModel`
  );

  if (response.status !== 200) {
    throw new Error(`Failed to fetch retriever components: ${response.statusText}`);
  }

  return response.data;

}

export const getGeneratorComponents = async (): Promise<IGenerativeTask[]> => {

  const response = await api.get(
    `/v1/component/?related_component=TextToTextGenerationTask`
  );

  if (response.status !== 200) {
    throw new Error(`Failed to fetch generator components: ${response.statusText}`);
  }

  return response.data;

}