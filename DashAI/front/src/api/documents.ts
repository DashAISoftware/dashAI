import api from "./api";
import type { IFolder } from "../types/folder";

const documentsEndpoint = "/v1/documents";
const documentsUrlBase = "/api/v1/documents";

export interface IDocumentSession {
  id: number;
  name: string;
}

export interface IDataDocument {
  id: number;
  name: string;
  file_name: string | null;
  file_type: string | null;
  file_path: string | null;
  dataloader: string | null;
  dataloader_params: Record<string, unknown> | null;
  content_counts: Record<string, number> | null;
  total_pages: number | null;
  folder_id: number | null;
  status: number;
  created: string;
  last_modified: string;
  sessions: IDocumentSession[];
}

export interface IDocumentContentItem {
  type: "Text" | "Image";
  position: number;
  page: number | null;
  kind: string;
  attrs: Record<string, unknown>;
  content?: string;
  url?: string;
}

export interface IDocumentContentPage {
  document_id: number;
  content_type: string;
  total: number;
  offset: number;
  limit: number;
  items: IDocumentContentItem[];
}

export interface IDocumentCreateParams {
  name: string;
  file_name: string;
  dataloader: string;
  dataloader_params: Record<string, unknown>;
  folder_id?: number | null;
}

/**
 * One document of a batch creation request.
 *
 * The bytes are not sent here: each document is created as a placeholder row
 * and its file is uploaded afterwards through its own DocumentJob.
 */
export interface IDocumentBatchFile {
  name: string;
  file_name: string;
  dataloader: string;
  dataloader_params: Record<string, unknown>;
}

export interface IDocumentBatchParams {
  /** Folder that groups every created document, or null for loose documents. */
  folder_name: string | null;
  files: IDocumentBatchFile[];
}

export interface IDocumentBatchResult {
  /** The folder created for the batch, or null when no folder was requested. */
  folder: IFolder | null;
  documents: IDataDocument[];
}

export const createDocumentFromNotebook = async (
  name: string,
  notebookId: number,
): Promise<IDataDocument> => {
  const response = await api.post<IDataDocument>(
    `${documentsEndpoint}/from-notebook`,
    { name, notebook_id: notebookId },
  );
  return response.data;
};

export const getDocuments = async (): Promise<IDataDocument[]> => {
  const response = await api.get<IDataDocument[]>(`${documentsEndpoint}/`);
  return response.data;
};

export const getDocument = async (id: number): Promise<IDataDocument> => {
  const response = await api.get<IDataDocument>(`${documentsEndpoint}/${id}`);
  return response.data;
};

export const createDocument = async (
  params: IDocumentCreateParams,
): Promise<IDataDocument> => {
  const response = await api.post<IDataDocument>(
    `${documentsEndpoint}/`,
    params,
  );
  return response.data;
};

/**
 * Creates a folder and its documents in a single atomic request.
 *
 * Either every row is created or none is: a duplicate name answers 409 and an
 * invalid loader, extension or parameter set answers 422, so the caller only
 * has to resolve conflicts once before retrying.
 *
 * @param params - Optional folder name and the placeholder for each file.
 * @returns The created folder (or null) and the placeholder documents.
 */
export const createDocumentsBatch = async (
  params: IDocumentBatchParams,
): Promise<IDocumentBatchResult> => {
  const response = await api.post<IDocumentBatchResult>(
    `${documentsEndpoint}/batch`,
    params,
  );
  return response.data;
};

export const updateDocument = async (
  id: number,
  data: { name?: string; folder_id?: number | null },
): Promise<IDataDocument> => {
  const response = await api.patch<IDataDocument>(
    `${documentsEndpoint}/${id}`,
    data,
  );
  return response.data;
};

export const deleteDocument = async (
  id: number,
  cascadeSessions = false,
): Promise<void> => {
  await api.delete(`${documentsEndpoint}/${id}`, {
    params: { cascade_sessions: cascadeSessions },
  });
};

export const getDocumentContent = async (
  id: number,
  contentType = "all",
  offset = 0,
  limit = 50,
): Promise<IDocumentContentPage> => {
  const response = await api.get<IDocumentContentPage>(
    `${documentsEndpoint}/${id}/content`,
    { params: { content_type: contentType, offset, limit } },
  );
  return response.data;
};

export interface IDocumentOutlineItem {
  position: number;
  type: "Text" | "Image";
  kind: string;
  page: number | null;
  level: number | null;
  label: string | null;
}

export interface IDocumentOutline {
  document_id: number;
  total: number;
  items: IDocumentOutlineItem[];
}

export const getDocumentOutline = async (
  id: number,
): Promise<IDocumentOutline> => {
  const response = await api.get<IDocumentOutline>(
    `${documentsEndpoint}/${id}/outline`,
  );
  return response.data;
};

export const getDocumentSourceViewUrl = (
  id: number,
  version?: string | null,
): string =>
  version
    ? `${documentsUrlBase}/${id}/source/view?v=${encodeURIComponent(version)}`
    : `${documentsUrlBase}/${id}/source/view`;

/**
 * Absolute URL of the inline source view, for iframes and new tabs.
 *
 * `getDocumentSourceViewUrl` is rooted at `/api`; in development the frontend
 * runs on another origin, so the API base URL has to be prefixed (and its
 * `/api` suffix removed to avoid `/api/api`).
 *
 * @param id - The document id.
 * @param version - Optional cache-busting version.
 * @returns The URL the browser can load directly.
 */
export const getDocumentSourceViewAbsoluteUrl = (
  id: number,
  version?: string | null,
): string => {
  const path = getDocumentSourceViewUrl(id, version);
  const base = (api.defaults.baseURL ?? "").replace(/\/$/, "");
  if (!base) return path;
  const suffix = base.endsWith("/api") ? path.replace(/^\/api/, "") : path;
  return `${base}${suffix}`;
};

export const getDocumentSourceDownloadUrl = (id: number): string =>
  `${documentsUrlBase}/${id}/source`;

export const enqueueDocumentJob = async (
  documentId: number,
  name: string,
  file: File,
): Promise<{ id: string }> => {
  const formData = new FormData();
  formData.append("job_type", "DocumentJob");
  formData.append("kwargs", JSON.stringify({ document_id: documentId, name }));
  formData.append("file", file);
  const response = await api.post<{ id: string }>("/v1/job/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
      filename: encodeURIComponent(file.name),
    },
  });
  return response.data;
};

export const enqueueHubDocumentJob = async (
  documentId: number,
  name: string,
  datafileId: number,
  selectedFile: string,
): Promise<{ id: string }> => {
  const formData = new FormData();
  formData.append("job_type", "DocumentJob");
  formData.append(
    "kwargs",
    JSON.stringify({
      document_id: documentId,
      name,
      datafile_id: datafileId,
      selected_file: selectedFile,
    }),
  );
  const response = await api.post<{ id: string }>("/v1/job/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};
