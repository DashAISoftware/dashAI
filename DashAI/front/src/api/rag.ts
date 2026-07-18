import api from "./api";
import { ISession } from "../types/session";
import { IGenerativeTask } from "../types/generativeTask";
import { IDocumentResponse } from "../types/documentResponse";
import { IComponent } from "../types/component";
import { IRAGPrompt } from "../types/ragPrompt";
import { getChildComponents } from "./component";

/**
 * Creates a new RAG prompt via the API.
 * @param prompt - The prompt data (class_name, name, optional parameters).
 * @returns The created prompt metadata containing the new ID.
 */
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

/** Fetches all generative sessions filtered to RAGTask. @returns List of RAG sessions. */
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

/** Fetches a single RAG session by ID. @param sessionId - The session ID. @returns The session object. */
export const getRAGSession = async (sessionId: number): Promise<ISession> => {
  const response = await api.get<ISession>(
    `/v1/generative-session/${sessionId}`,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG session: ${response.statusText}`);
  }

  return response.data;
};

/**
 * Creates a new RAG session with the given data, forcing task_name to "RAGTask".
 * @param sessionData - Session creation payload (without id/created/last_modified).
 * @returns The created session.
 */
export const createRAGSession = async (
  sessionData: Omit<ISession, "id" | "created" | "last_modified">,
): Promise<ISession> => {
  const transformedSession: Omit<ISession, "id" | "created" | "last_modified"> =
    {
      name: sessionData.name,
      description: sessionData.description,
      task_name: "RAGTask",
      model_name: "RAGPipeline",
      display_name: "",
      parameters: sessionData.parameters,
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

/** Updates an existing RAG session. @param sessionId - The session ID. @param sessionData - Partial fields to update. @returns The updated session. */
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

/** Deletes a RAG session by ID. @param sessionId - The session ID. */
export const deleteRAGSession = async (sessionId: number): Promise<void> => {
  const response = await api.delete(`/v1/generative-session/${sessionId}`);
  if (response.status !== 204) {
    throw new Error(`Failed to delete RAG session: ${response.statusText}`);
  }
};

/** Updates only the parameters of an existing RAG session. @param sessionId - The session ID. @param newParams - The new parameters payload. @returns The updated session. */
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

/** Fetches all available retriever paradigms (children of RetrieverModel). @returns List of retriever paradigm components. */
export const getRetrievalParadigm = async (): Promise<IComponent[]> => {
  const response = await getChildComponents("RetrieverModel", true);
  if (!response) {
    throw new Error(`Failed to fetch retrieval options`);
  }
  return response;
};

/** Fetches child components (specific retrievers) for a given retrieval paradigm. @param retrievalParadigm - Parent paradigm name. @returns List of retriever components. */
export const getRetrieverComponents = async (
  retrievalParadigm: string,
): Promise<IComponent[]> => {
  const response = await getChildComponents(retrievalParadigm, true);

  if (!response) {
    throw new Error(`Failed to fetch retriever components`);
  }

  return response;
};

/** Fetches generator components related to TextToTextGenerationTask. @returns List of generator components. */
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

/** Fetches chunking model components (children of BaseChunkingModel). @returns List of chunking components. */
export const getChunkingComponents = async (): Promise<IComponent[]> => {
  const response = await getChildComponents("BaseChunkingModel", false);
  if (!response) {
    throw new Error(`Failed to fetch chunking components`);
  }
  return response;
};

/** Fetches all uploaded documents. @returns List of document responses. */
export const loadDocuments = async (): Promise<IDocumentResponse[]> => {
  const response = await api.get<IDocumentResponse[]>("/v1/document/");
  if (response.status !== 200) {
    throw new Error(`Failed to load documents: ${response.statusText}`);
  }
  return response.data;
};

/** Fetches documents scoped to a specific RAG session. @param sessionId - The session ID. @returns List of document responses. */
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

/** Deletes a document by ID. @param documentId - The document ID. */
export const deleteDocument = async (documentId: number): Promise<void> => {
  const response = await api.delete(`/v1/document/${documentId}`);
  if (response.status !== 204) {
    throw new Error(`Failed to delete document: ${response.statusText}`);
  }
};

/**
 * Uploads a document file with optional metadata via multipart/form-data.
 * @param file - The File object to upload.
 * @param optional_metadata - Optional metadata (name, source, etc.).
 * @returns The saved document response.
 */
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

/** Class name prefix that identifies non-generation prompt types. */
const AUGMENTATION_PROMPT_CLASS_PREFIX = "Augmentation";

/**
 * Checks whether a prompt's class_name corresponds to a generation prompt
 * (i.e. NOT an augmentation prompt).
 *
 * @param className - The prompt component class name to test.
 * @returns `true` if the class is a generation prompt, `false` if it is an augmentation prompt.
 */
export function isGenerationPromptClass(className: string): boolean {
  return !className.includes(AUGMENTATION_PROMPT_CLASS_PREFIX);
}

/** Fetches default prompt components (children of RAGGenerationPrompt). @returns List of default prompt components. */
export const getDefaultPrompts = async (): Promise<IComponent[]> => {
  return getChildComponents("RAGGenerationPrompt", false);
};

/** Fetches all saved RAG prompts (user-created). @returns List of RAG prompts. */
export const getRAGPrompts = async (): Promise<IRAGPrompt[]> => {
  const response = await api.get<IRAGPrompt[]>("/v1/prompt/");
  if (response.status !== 200) {
    throw new Error(`Failed to fetch RAG prompts: ${response.statusText}`);
  }
  return response.data;
};

/**
 * Fetches custom (non-Default) prompt components for the given parent types.
 * @param types - Array of parent component type names to fetch children from.
 * @returns List of custom prompt components (excluding Default* classes).
 */
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
