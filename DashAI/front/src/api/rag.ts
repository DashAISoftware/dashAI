import api from "./api";
import { ISession } from "../types/session";
import { IGenerativeTask } from "../types/generativeTask";
import { IComponent } from "../types/component";
import { RetrieverPresetRecipe } from "../types/retrieverPreset";
import {
  IRAGConfiguration,
  IRAGIndexStatus,
  IRAGPreset,
} from "../types/ragConfiguration";
import { getChildComponents } from "./component";
import { ISessionDocument } from "../types/sessionDocument";
import { RAG_WORKFLOW_NAME } from "../constants/generativeWorkflows";

export interface IRAGSessionCreate {
  name: string;
  description: string;
  parameters: {
    generation_model: { component: string; params: Record<string, any> };
    [key: string]: any;
  };
}

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
 * Creates a new RAG session run by the RAG workflow, whose model is the chosen generator.
 * @param sessionData - Name, description and parameters of the new session.
 * @returns The created session.
 */
export const createRAGSession = async (
  sessionData: IRAGSessionCreate,
): Promise<ISession> => {
  const response = await api.post<ISession>("/v1/generative-session/", {
    name: sessionData.name,
    description: sessionData.description,
    workflow_name: RAG_WORKFLOW_NAME,
    model_name: sessionData.parameters.generation_model.component,
    parameters: sessionData.parameters,
  });

  if (response.status !== 201) {
    throw new Error(`Failed to create RAG session: ${response.statusText}`);
  }

  return response.data;
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

/** Fetches all available retriever paradigms (children of BaseRetriever). @returns List of retriever paradigm components. */
export const getRetrievalParadigm = async (): Promise<IComponent[]> => {
  const response = await getChildComponents("BaseRetriever", true);
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

/**
 * Fetches resolved retriever preset recipes for a given top-K.
 * @param topK - Number of chunks to configure.
 * @returns List of preset recipes ({ key, description, component, params }).
 */
export const getRetrieverPresets = async (
  topK: number,
): Promise<RetrieverPresetRecipe[]> => {
  const response = await api.get("/v1/rag/retriever-presets", {
    params: { top_k: topK },
  });
  if (response.status !== 200) {
    throw new Error(
      `Failed to fetch retriever presets: ${response.statusText}`,
    );
  }
  return response.data;
};

/**
 * Fetches resolved chunking preset recipes.
 * Names and summaries are localized by the backend, so they render as-is.
 * @returns List of chunking presets.
 */
export const getChunkingPresets = async (): Promise<IRAGPreset[]> => {
  const response = await api.get<IRAGPreset[]>("/v1/rag/chunking-presets");
  if (response.status !== 200) {
    throw new Error(`Failed to fetch chunking presets: ${response.statusText}`);
  }
  return response.data;
};

/**
 * Fetches a session's configuration already resolved into friendly labels.
 * @param sessionId - The RAG session ID.
 * @returns Display names, preset labels, labelled parameters and the context budget.
 */
export const getSessionConfiguration = async (
  sessionId: number,
): Promise<IRAGConfiguration> => {
  const response = await api.get<IRAGConfiguration>(
    `/v1/rag/sessions/${sessionId}/configuration`,
  );
  if (response.status !== 200) {
    throw new Error(
      `Failed to fetch session configuration: ${response.statusText}`,
    );
  }
  return response.data;
};

/**
 * Fetches whether a session's documents are indexed for its current config.
 * Read-only: it never triggers indexing, so it is safe to poll while an
 * indexing job runs.
 * @param sessionId - The RAG session ID.
 * @returns The indexing status, with a localized message ready to render.
 */
export const getSessionIndexStatus = async (
  sessionId: number,
): Promise<IRAGIndexStatus> => {
  const response = await api.get<IRAGIndexStatus>(
    `/v1/rag/sessions/${sessionId}/index-status`,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to fetch index status: ${response.statusText}`);
  }
  return response.data;
};

/**
 * Starts indexing a session's documents, unless there is nothing to do.
 *
 * Safe to call after any change: the backend already owns the rule for which
 * settings invalidate the index, and short-circuits when the documents are
 * already indexed or a job is running. Deciding that here too could only
 * drift from it.
 *
 * @param sessionId - The RAG session ID.
 * @returns The resulting index status, so no follow-up fetch is needed.
 */
export const startSessionIndexing = async (
  sessionId: number,
): Promise<IRAGIndexStatus> => {
  const response = await api.post<IRAGIndexStatus>(
    `/v1/rag/sessions/${sessionId}/index`,
  );
  if (response.status !== 202 && response.status !== 200) {
    throw new Error(`Failed to start indexing: ${response.statusText}`);
  }
  return response.data;
};

/** Fetches generator components related to TextToTextGenerationTask. @returns List of generator components. */
export const getGeneratorComponents = async (): Promise<IGenerativeTask[]> => {
  const response = await api.get(
    `/v1/component/?related_component=TextToTextGenerationTask&select_types=GenerativeModel`,
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

export const listSessionDocuments = async (
  sessionId: number | string,
): Promise<ISessionDocument[]> => {
  const response = await api.get<ISessionDocument[]>(
    `/v1/rag/sessions/${sessionId}/documents`,
  );
  if (response.status !== 200) {
    throw new Error(`Failed to load session documents: ${response.statusText}`);
  }
  return response.data;
};

export const attachSessionDocuments = async (
  sessionId: number | string,
  documentIds: number[],
): Promise<ISessionDocument[]> => {
  const response = await api.post<ISessionDocument[]>(
    `/v1/rag/sessions/${sessionId}/documents`,
    { document_ids: documentIds },
  );
  if (response.status !== 200) {
    throw new Error(`Failed to attach documents: ${response.statusText}`);
  }
  return response.data;
};

export const detachSessionDocument = async (
  sessionId: number | string,
  documentId: number,
): Promise<void> => {
  const response = await api.delete(
    `/v1/rag/sessions/${sessionId}/documents/${documentId}`,
  );
  if (response.status !== 204) {
    throw new Error(`Failed to detach document: ${response.statusText}`);
  }
};

/** Fetches default prompt components (children of RAGGenerationPrompt). @returns List of default prompt components. */
export const getDefaultPrompts = async (): Promise<IComponent[]> => {
  return getChildComponents("RAGGenerationPrompt", false);
};

/**
 * Fetches query transformation components (children of BaseQueryTransformation).
 * @returns List of transformer components, each carrying `metadata.technique`
 *   ("rewriting" | "expansion" | "decomposition") and `metadata.prompt_parent`.
 */
export const getQueryTransformationComponents = async (): Promise<
  IComponent[]
> => {
  const response = await getChildComponents("BaseQueryTransformation", true);
  if (!response) {
    throw new Error(`Failed to fetch query transformation components`);
  }
  return response;
};

/**
 * Fetches query transformation prompts (children of QueryTransformationPrompt).
 * @returns List of prompt components, each carrying `metadata.technique` and
 *   `metadata.variant` ("default" | "custom").
 */
export const getQueryTransformationPrompts = async (): Promise<
  IComponent[]
> => {
  const response = await getChildComponents("QueryTransformationPrompt", true);
  if (!response) {
    throw new Error(`Failed to fetch query transformation prompts`);
  }
  return response;
};
