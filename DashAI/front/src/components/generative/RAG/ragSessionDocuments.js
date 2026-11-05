import { DOCUMENT_STATUS } from "../../../hooks/datasets/useDocuments";
import { getDocuments } from "../../../api/documents";

/**
 * Keeps only the selected ids that still point to a finished document.
 *
 * The selection can outlive the library rows it was made from (a document may
 * be deleted or start reprocessing while the create form is open), so the ids
 * are checked against the fresh library right before they are attached.
 *
 * @param {Array<number>} selectedIds - Ids picked by the user.
 * @param {Array<object>} library - Documents returned by `getDocuments`.
 * @returns {Array<number>} The ids that can still be attached.
 */
export function filterSelectableDocumentIds(selectedIds, library) {
  const finishedIds = new Set(
    library
      .filter((document) => document.status === DOCUMENT_STATUS.FINISHED)
      .map((document) => document.id),
  );
  return selectedIds.filter((id) => finishedIds.has(id));
}

/**
 * Reads the library (with one retry) and keeps the attachable selected ids.
 *
 * A single transient GET failure must not silently create a session without the
 * documents the user picked, so the read is retried once. When both attempts
 * fail the result says the validation failed and the caller decides to create
 * the session without documents.
 *
 * @param {Array<number>} selectedIds - Ids picked by the user.
 * @param {Function} [loadDocuments] - Library reader, injectable for tests.
 * @returns {Promise<{ids: Array<number>|null, skipped: number, validationFailed: boolean}>}
 *   The attachable ids, how many were dropped, and whether the library could
 *   not be read after both attempts.
 */
export async function resolveAttachableIds(
  selectedIds,
  loadDocuments = getDocuments,
) {
  let lastError = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const library = await loadDocuments();
      const ids = filterSelectableDocumentIds(selectedIds, library);
      return {
        ids,
        skipped: selectedIds.length - ids.length,
        validationFailed: false,
      };
    } catch (error) {
      lastError = error;
    }
  }
  console.error("Failed to validate the selected documents:", lastError);
  return { ids: null, skipped: 0, validationFailed: true };
}

/**
 * Attaches documents to a freshly created session, undoing it on failure.
 *
 * A session created without the documents the user picked is not what they
 * asked for, so a failed attach removes it again. The caller decides what to
 * report: `rollbackFailed` means the session may still exist in the backend and
 * the session list should be refetched.
 *
 * @param {object}   params
 * @param {string|number} params.sessionId - The session just created.
 * @param {Array<number>} params.documentIds - Ids to attach.
 * @param {Function} params.attach - Attach call, `(sessionId, ids) => Promise`.
 * @param {Function} params.remove - Remove call, `(sessionId) => Promise`.
 * @returns {Promise<{ok: boolean, error?: unknown, rollbackFailed?: boolean,
 *   rollbackError?: unknown}>} `ok` when the attach worked; otherwise the
 *   attach error. `rollbackFailed` is set when removing the session also
 *   failed, and `rollbackError` carries that second failure.
 */
export async function attachDocumentsOrRollback({
  sessionId,
  documentIds,
  attach,
  remove,
}) {
  try {
    await attach(sessionId, documentIds);
    return { ok: true };
  } catch (error) {
    try {
      await remove(sessionId);
      return { ok: false, error };
    } catch (rollbackError) {
      return { ok: false, error, rollbackFailed: true, rollbackError };
    }
  }
}

/**
 * Builds the attach step of the create flow, including its rollback reporting.
 *
 * @param {object}   params
 * @param {Function} params.attach - Attach call, `(sessionId, ids) => Promise`.
 * @param {Function} params.remove - Remove call, `(sessionId) => Promise`.
 * @param {Function} params.onAttachFailed - Reports the attach error.
 * @param {Function} params.onRollbackFailed - Reports the failed rollback.
 * @param {Function} params.refreshSessions - Refetches the session list
 *   without a second error toast.
 * @returns {Function} `(created, ids) => Promise<boolean>`, true when the
 *   session is ready to be kept.
 */
export function createAttachCreatedSession({
  attach,
  remove,
  onAttachFailed,
  onRollbackFailed,
  refreshSessions,
}) {
  return async function attachCreatedSession(created, ids) {
    if (ids.length === 0) return true;

    const result = await attachDocumentsOrRollback({
      sessionId: created.id,
      documentIds: ids,
      attach,
      remove,
    });
    if (result.ok) return true;

    if (result.rollbackFailed) {
      console.error(
        "Failed to roll back the RAG session:",
        result.rollbackError,
      );
      await refreshSessions();
      onRollbackFailed();
      return false;
    }

    onAttachFailed(result.error);
    return false;
  };
}
