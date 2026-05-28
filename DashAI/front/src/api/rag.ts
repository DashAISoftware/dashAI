import api from "./api";
import { ISession } from "../types/session";
import { IGenerativeTask } from "../types/generativeTask";
import { IDocumentResponse } from "../types/documentResponse";
import { IComponent } from "../types/component";
import { IRAGPrompt } from "../types/ragPrompt";
import { getChildComponents } from "./component";

export const createRAGPrompt = async (prompt: {
  class_name: string;
  name: string;
  parameters?: Record<string, any>;
}): Promise<{ id: number }> => {
  const response = await api.post("/v1/prompt/", prompt);
  if (response.status !== 201) {
    throw new Error(`Failed to create RAG prompt: ${response.statusText}`);
  }
  return response.data;
};

export const getRAGSessions = async (): Promise<ISession[]> => {
  const response = await api.get<ISession[]>("/v1/generative-session/");
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG sessions: ${response.statusText}`);
  }

  const ragSessions = response.data.filter(
    (session) => session.task_name === "RAGTask",
  );
  return ragSessions;
};

export const getRAGSession = async (sessionId: number): Promise<ISession> => {
  const response = await api.get<ISession>(
    `/v1/generative-session/${sessionId}`,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG session: ${response.statusText}`);
  }

  return response.data;
};

export const createRAGSession = async (
  sessionData: Omit<ISession, "id" | "created" | "last_modified">,
): Promise<ISession> => {
  console.log("Creating RAG session with data:", sessionData);
  const params = sessionData.parameters as {
    documents: number[];
    chunking_model: {
      component: string;
      params: Record<string, any>;
    };
    retriever_model: {
      component: string;
      params: Record<string, any>;
    };
    generation_model: {
      component: string;
      params: Record<string, any>;
    };
    prompt: {
      component: string;
      params: Record<string, any>;
    };
  };

  const transformedSession: Omit<ISession, "id" | "created" | "last_modified"> =
    {
      name: sessionData.name,
      description: sessionData.description,
      task_name: "RAGTask",
      model_name: "RAGPipeline",
      display_name: "",
      parameters: {
        documents: params.documents,
        chunking_model: {
          component: params.chunking_model.component,
          params: params.chunking_model.params,
        },
        retriever_model: {
          component: params.retriever_model.component,
          params: params.retriever_model.params,
        },
        generation_model: {
          component: params.generation_model.component,
          params: params.generation_model.params,
        },
        prompt: params.prompt,
      },
    };

  const response = await api.post<ISession>(
    "/v1/generative-session/",
    transformedSession,
  );

  if (response.status !== 201) {
    throw new Error(`Failed to create RAG session: ${response.statusText}`);
  }

  return response.data;
};

export const updateRAGSession = async (
  sessionId: number,
  sessionData: Partial<ISession>,
): Promise<ISession> => {
  const response = await api.put<ISession>(
    `/v1/generative-session/${sessionId}`,
    sessionData,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to update RAG session: ${response.statusText}`);
  }

  return response.data;
};

export const deleteRAGSession = async (sessionId: number): Promise<void> => {
  const response = await api.delete(`/v1/generative-session/${sessionId}`);
  if (response.status !== 204) {
    throw new Error(`Failed to delete RAG session: ${response.statusText}`);
  }
};

export const updateGenerativeSessionParams = async (
  sessionId: number,
  newParams: Record<string, any>,
): Promise<ISession> => {
  const response = await api.put<ISession>(
    `/v1/generative-session/${sessionId}/parameters`,
    newParams,
  );
  if (response.status !== 200) {
    throw new Error(
      `Failed to update RAG session parameters: ${response.statusText}`,
    );
  }
  return response.data;
};

export const getRetrievalParadigm = async (): Promise<IComponent[]> => {
  const response = getChildComponents("RetrieverModel", true);
  if (!response) {
    throw new Error(`Failed to fetch retrieval options`);
  }
  return response;
};

export const getRetrieverComponents = async (
  retrievalParadigm: string,
): Promise<IComponent[]> => {
  const response = getChildComponents(retrievalParadigm, false);

  if (!response) {
    throw new Error(`Failed to fetch retriever components`);
  }

  return response;
};

export const getGeneratorComponents = async (): Promise<IGenerativeTask[]> => {
  const response = await api.get(
    `/v1/component/?related_component=TextToTextGenerationTask`,
  );

  if (response.status !== 200) {
    throw new Error(
      `Failed to fetch generator components: ${response.statusText}`,
    );
  }

  return response.data;
};

export const getChunkingComponents = async (): Promise<IComponent[]> => {
  const response = await getChildComponents("BaseChunkingModel", false);
  if (!response) {
    throw new Error(`Failed to fetch chunking components`);
  }
  return response;
};

export const loadDocuments = async (): Promise<IDocumentResponse[]> => {
  const response = await api.get<IDocumentResponse[]>("/v1/document/");
  if (response.status !== 200) {
    throw new Error(`Failed to load documents: ${response.statusText}`);
  }
  return response.data;
};

export const getSessionDocuments = async (
  sessionId: number,
): Promise<IDocumentResponse[]> => {
  const response = await api.get<IDocumentResponse[]>(
    `/v1/document/session/${sessionId}`,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to load session documents: ${response.statusText}`);
  }
  return response.data;
};

export const deleteDocument = async (documentId: number): Promise<void> => {
  const response = await api.delete(`/v1/document/${documentId}`);
  if (response.status !== 204) {
    throw new Error(`Failed to delete document: ${response.statusText}`);
  }
};

export const addDocument = async ({
  file,
  optional_metadata,
}: {
  file: File;
  optional_metadata?: Record<string, any>;
}): Promise<IDocumentResponse> => {
  if (optional_metadata) {
    optional_metadata.last_modified = file.lastModified;
  }
  const metadata = {
    file_name: file.name,
    last_modified: file.lastModified,
    optional_metadata,
  };

  const formData = new FormData();
  formData.append("file", file);
  formData.append("metadata", JSON.stringify(metadata));

  const response = await api.post<IDocumentResponse>(
    "/v1/document/",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );

  if (response.status !== 201) {
    throw new Error(`Failed to upload document: ${response.statusText}`);
  }

  return response.data;
};

export const getDefaultPrompts = async (): Promise<IComponent[]> => {
  return getChildComponents("RAGGenerationPrompt", false);
};

export const getRAGPrompts = async (): Promise<IRAGPrompt[]> => {
  const response = await api.get<IRAGPrompt[]>("/v1/prompt/");
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG prompts: ${response.statusText}`);
  }
  return response.data;
};

export const getCustomPrompts = async (
  types: string[] = ["RAGGenerationPrompt", "AugmentationPrompt"],
): Promise<IComponent[]> => {
  let allChildren: IComponent[] = [];
  for (const type of types) {
    const response = await api.get<IComponent[]>(
      `/v1/component/${type}/children`,
      { params: { recursive: false } },
    );
    if (response.status !== 200) {
      throw new Error(
        `Failed to fetch ${type} children: ${response.statusText}`,
      );
    }
    const filtered = response.data.filter(
      (child) =>
        !(
          child.name &&
          typeof child.name === "string" &&
          child.name.includes("Default")
        ),
    );
    allChildren.push(...filtered);
  }
  return allChildren;
};
