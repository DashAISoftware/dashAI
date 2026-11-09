/**
 * Shared limits and enums for the RAG folder/file upload dialog.
 *
 * Keeping the values here instead of inside each component means the picker,
 * the orchestrating hook and the progress panel all agree on what a status or
 * a skip reason is, and no raw string crosses between them.
 */

/** Largest file the upload accepts; larger ones are skipped before sending. */
export const MAX_FILE_SIZE_BYTES = 4 * 1024 ** 3;

/**
 * Above this many accepted files the dialog asks for confirmation first.
 * The upload is not blocked, only announced: files are processed one at a time.
 */
export const UPLOAD_WARNING_THRESHOLD = 100;

/** Longest a single DocumentJob may stay pending before it is reconciled. */
export const JOB_TIMEOUT_MS = 20 * 60 * 1000;

/** Longest the close flow waits for the partial attach before closing anyway. */
export const ATTACH_CLOSE_TIMEOUT_MS = 10 * 1000;

/** How the selected files are attached to Data. */
export const UPLOAD_MODE = Object.freeze({
  FILE: "file",
  FOLDER: "folder",
});

/** Whether the document loaders have been fetched yet. */
export const LOADERS_STATUS = Object.freeze({
  LOADING: "loading",
  READY: "ready",
  ERROR: "error",
});

/** Whether the document converters have been fetched yet. */
export const CONVERTERS_STATUS = Object.freeze({
  LOADING: "loading",
  READY: "ready",
  ERROR: "error",
});

/** Content types a document can actually hold. */
export const DOCUMENT_CONTENT_TYPES = Object.freeze(["Text", "Image"]);

/**
 * @param {object} converter - A document converter component.
 * @returns {Array<string>} The document content types it declares, empty when
 *   it is unrestricted.
 */
export function documentConverterTypes(converter) {
  const types =
    converter?.metadata?.document_allowed_types ??
    converter?.metadata?.allowed_types;
  if (!Array.isArray(types)) return [];
  return types.filter((type) => DOCUMENT_CONTENT_TYPES.includes(type));
}

/** 409 detail fragment that identifies a name clash the batch can retry. */
export const NAME_CONFLICT_DETAIL = "already exists";

/** Lifecycle of a single upload run. */
export const UPLOAD_PHASE = Object.freeze({
  SELECTING: "selecting",
  UPLOADING: "uploading",
  PROCESSING: "processing",
  DONE: "done",
});

/** Whether the finished documents were attached to the session. */
export const ATTACH_STATUS = Object.freeze({
  IDLE: "idle",
  PENDING: "pending",
  DONE: "done",
  FAILED: "failed",
});

/** Per-file status shown in the progress panel. */
export const FILE_STATUS = Object.freeze({
  PENDING: "pending",
  UPLOADING: "uploading",
  QUEUED: "queued",
  PROCESSING: "processing",
  READY: "ready",
  ERROR: "error",
});

/** Why the picker left a selected file out of the upload. */
export const SKIP_REASON = Object.freeze({
  HIDDEN: "hidden",
  SYSTEM: "system",
  EMPTY: "empty",
  TOO_LARGE: "tooLarge",
  UNSUPPORTED: "unsupported",
  READ_ERROR: "readError",
});

/** Why a file (or the whole batch) could not become a document. */
export const FAILURE_CODE = Object.freeze({
  PARSE: "parseFailed",
  CANCELLED: "cancelled",
  ENQUEUE: "enqueueFailed",
  BATCH: "batchFailed",
  FOLDER_NAME: "folderNameRequired",
  PARSER: "parserRequired",
  TIMEOUT: "timeout",
  ATTACH: "attachFailed",
});

/** Names every OS drops into folders but no user wants to upload. */
export const SYSTEM_FILE_NAMES = Object.freeze(["thumbs.db", "desktop.ini"]);

/**
 * Formats a byte count for the skipped-files message.
 *
 * @param {number} bytes - The size to format.
 * @returns {string} A short human readable size, e.g. "4 GB".
 */
export function formatFileSize(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const rounded = Number.isInteger(value) ? value : value.toFixed(1);
  return `${rounded} ${units[unitIndex]}`;
}
