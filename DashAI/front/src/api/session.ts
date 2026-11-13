import api from "./api";
import type {
  IGenerativeSessionExportPreview,
  IGenerativeSessionImportResult,
  ISession,
} from "../types/session";

/**
 * Fetches generative sessions, optionally narrowed by the backend.
 * @param filters.taskName - Only sessions of this generative task. A view
 *   scoped to one task uses this; the shared list asks for everything.
 * @returns The matching sessions, oldest first.
 */
export const getSessions = async (filters?: {
  taskName?: string;
}): Promise<ISession[]> => {
  const params: Record<string, string> = {};
  if (filters?.taskName) params.task_name = filters.taskName;
  const response = await api.get<ISession[]>("/v1/generative-session", {
    params,
  });
  return response.data;
};

export const removeSession = async (
  sessionId: string | number,
): Promise<void> => {
  await api.delete(`/v1/generative-session/${sessionId}`);
};

export const removeSessions = async (ids: number[]): Promise<void> => {
  await api.delete("/v1/generative-session/", { data: { ids } });
};

export const getSessionById = async (sessionId: string): Promise<ISession> => {
  const response = await api.get<ISession>(
    `/v1/generative-session/${sessionId}`,
  );
  return response.data;
};

export const getHistoryBySessionId = async (
  sessionId: string,
): Promise<ISession[]> => {
  const response = await api.get<ISession[]>(
    `/v1/generative-session/parameters-history/${sessionId}`,
  );
  return response.data;
};

export const updateGenerativeSession = async ({
  id,
  formData,
}: {
  id: string;
  formData: {
    name?: string;
    task_name?: string;
    description?: string;
    model_name?: string;
  };
}): Promise<object> => {
  const response = await api.patch(`/v1/generative-session/${id}`, null, {
    params: formData,
  });
  return response.data;
};

/**
 * What exporting a generative session would carry.
 * @param sessionId - The session to export.
 * @returns Its conversation size and how many messages would be left out.
 */
export const getGenerativeSessionExportPreview = async (
  sessionId: number,
): Promise<IGenerativeSessionExportPreview> => {
  const response = await api.get<IGenerativeSessionExportPreview>(
    `/v1/generative-session/${sessionId}/export/preview`,
  );
  return response.data;
};

/**
 * Downloads a generative session as a .dashai file.
 * @param sessionId - The session to export.
 * @param options.includeConversation - Also carry the finished messages and
 *   their media files.
 * @returns The file contents.
 */
export const exportGenerativeSession = async (
  sessionId: number,
  options: { includeConversation?: boolean } = {},
): Promise<Blob> => {
  const response = await api.post(
    `/v1/generative-session/${sessionId}/export`,
    { include_conversation: Boolean(options.includeConversation) },
    { responseType: "blob" },
  );
  return response.data;
};

/**
 * Creates a new generative session from a .dashai file.
 * @param file - The file the user chose.
 * @returns The new session and what it still needs before use.
 */
export const importGenerativeSession = async (
  file: File,
): Promise<IGenerativeSessionImportResult> => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post<IGenerativeSessionImportResult>(
    "/v1/generative-session/import",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
};
