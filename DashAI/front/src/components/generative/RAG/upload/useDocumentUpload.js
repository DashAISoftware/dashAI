import { useCallback, useEffect, useRef, useState } from "react";
import {
  createDocumentsBatch,
  deleteDocument,
  enqueueDocumentJob,
  getDocument,
  getDocuments,
} from "../../../../api/documents";
import { deleteFolder, getFolders } from "../../../../api/folders";
import {
  CANCELLED_JOB_STATUSES,
  startJobPolling,
  stopJobPolling,
} from "../../../../utils/jobPoller";
import { getApiErrorMessage } from "../../../../utils/apiError";
import { DOCUMENT_STATUS } from "../../../../hooks/datasets/useDocuments";
import { getFileExtension, uniqueName } from "./fileSelection";
import {
  ATTACH_STATUS,
  FAILURE_CODE,
  FILE_STATUS,
  JOB_TIMEOUT_MS,
  UPLOAD_MODE,
  UPLOAD_PHASE,
} from "./uploadConstants";

const EMPTY_PROGRESS = Object.freeze({
  completed: 0,
  total: 0,
  items: [],
});

const EMPTY_ATTACH = Object.freeze({
  status: ATTACH_STATUS.IDLE,
  ids: [],
  failure: null,
});

const TERMINAL_FILE_STATUSES = [FILE_STATUS.READY, FILE_STATUS.ERROR];

/**
 * @param {{relativePath: string}} entry - A selection entry.
 * @param {number} index - Its position in the selection.
 * @returns {string} The key the progress panel uses for it.
 */
function entryKey(entry, index) {
  return `${entry.relativePath}#${index}`;
}

/**
 * Indexes the created documents by name so each file can find its own row.
 *
 * @param {Array<object>} documents - The created documents.
 * @returns {Map<string, object>} Documents keyed by name.
 */
function indexDocumentsByName(documents) {
  const byName = new Map();
  for (const document of documents) {
    byName.set(document.name, document);
  }
  return byName;
}

/**
 * Picks the document a batch created for a given file.
 *
 * @param {Map<string, object>} byName - Created documents keyed by name.
 * @param {Array<object>} documents - The created documents, in request order.
 * @param {object} file - The batch file that was sent.
 * @param {number} index - Its position in the batch.
 * @returns {object|undefined} The matching document.
 */
function matchDocument(byName, documents, file, index) {
  return byName.get(file.name) ?? documents[index];
}

/**
 * @param {string} status - A job status.
 * @returns {boolean} Whether the job stopped instead of failing.
 */
function isCancelledStatus(status) {
  return CANCELLED_JOB_STATUSES.includes(status);
}

/**
 * Builds the batch payload, resolving every name against the fresh data.
 *
 * @param {object} params - Batch inputs.
 * @param {string} params.mode - "file" or "folder".
 * @param {string} params.folderName - Folder name typed by the user.
 * @param {Array} params.entries - Accepted selection entries.
 * @param {Record<string, {loaderName: string, params: object}>} params.parsers
 *   Parser and parameters for each extension.
 * @param {Array<object>} params.documents - Documents already in Data.
 * @param {Array<object>} params.folders - Folders already in Data.
 * @returns {{folderName: string|null, files: Array<object>, renamedCount: number}}
 *   The payload and how many document names had to be made unique.
 */
function buildBatchPayload({
  mode,
  folderName,
  entries,
  parsers,
  documents,
  folders,
}) {
  const usedNames = new Set(documents.map((document) => document.name));
  let renamedCount = 0;
  const files = entries.map((entry) => {
    const extension = getFileExtension(entry.file.name);
    const parser = parsers[extension];
    if (!parser) {
      throw new Error(`No parser configured for "${entry.file.name}".`);
    }
    const name = uniqueName(entry.file.name, usedNames);
    if (name !== entry.file.name) renamedCount += 1;
    usedNames.add(name);
    return {
      name,
      file_name: entry.file.name,
      dataloader: parser.loaderName,
      dataloader_params: parser.params,
    };
  });

  const folderNameForBatch =
    mode === UPLOAD_MODE.FOLDER
      ? uniqueName(folderName, new Set(folders.map((folder) => folder.name)))
      : null;

  return { folderName: folderNameForBatch, files, renamedCount };
}

/**
 * Collects the documents of a selection that never got an enqueue request.
 *
 * @param {object} params - Lookup inputs.
 * @param {Array} params.entries - Accepted selection entries.
 * @param {Array} params.files - Batch files, in the same order as `entries`.
 * @param {Map<string, object>} params.byName - Documents keyed by name.
 * @param {Array<object>} params.documents - Created documents, in order.
 * @param {number} params.fromIndex - First entry that was not enqueued.
 * @returns {Array<object>} The documents to discard.
 */
function collectUnstarted({ entries, files, byName, documents, fromIndex }) {
  const unstarted = [];
  for (let index = fromIndex; index < entries.length; index += 1) {
    const document = matchDocument(byName, documents, files[index], index);
    if (document) unstarted.push(document);
  }
  return unstarted;
}

/**
 * Orchestrates a batch upload of files (optionally into a new folder).
 *
 * A run creates placeholder documents with a single batch request, uploads each
 * file through its own job, waits for every job, and only then reports the
 * documents that finished so the caller attaches them once. The run can be
 * aborted at any point: pending jobs are stopped and their waiters resolved, so
 * the dialog is never left waiting on a job that will not finish.
 *
 * @param {object} [options] - Hook options.
 * @param {Function} [options.onReady] - Attaches finished document ids to the
 *   session. Returns false when the attach failed.
 * @returns {object} The run state plus `start`, `abort`, `reset`,
 *   `retryAttach` and `attachReadyNow`.
 */
export default function useDocumentUpload({ onReady } = {}) {
  const [phase, setPhase] = useState(UPLOAD_PHASE.SELECTING);
  const [progress, setProgress] = useState(EMPTY_PROGRESS);
  const [failures, setFailures] = useState([]);
  const [skipped, setSkipped] = useState([]);
  const [busy, setBusy] = useState(false);
  const [attach, setAttach] = useState(EMPTY_ATTACH);
  const [resolvedFolderName, setResolvedFolderName] = useState(null);
  const [renamedCount, setRenamedCount] = useState(0);
  const mountedRef = useRef(true);
  const runningRef = useRef(false);
  const runIdRef = useRef(0);
  const pendingJobsRef = useRef(new Map());
  const readyIdsRef = useRef(new Set());
  const attachNowRef = useRef(false);
  const progressRef = useRef(EMPTY_PROGRESS);

  useEffect(() => {
    progressRef.current = progress;
  }, [progress]);

  const updateProgress = useCallback((updater) => {
    if (mountedRef.current) setProgress(updater);
  }, []);

  const updateItem = useCallback(
    (key, patch) => {
      updateProgress((previous) => ({
        ...previous,
        items: previous.items.map((item) =>
          item.key === key ? { ...item, ...patch } : item,
        ),
      }));
    },
    [updateProgress],
  );

  /**
   * Resolves every pending job waiter as aborted and stops its polling.
   */
  const abortPendingJobs = useCallback(() => {
    const pending = pendingJobsRef.current;
    for (const [jobId, entry] of [...pending.entries()]) {
      if (entry.timer != null) clearTimeout(entry.timer);
      stopJobPolling(jobId);
      pending.delete(jobId);
      entry.resolve({ failed: true, aborted: true });
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      runIdRef.current += 1;
      runningRef.current = false;
      abortPendingJobs();
    };
  }, [abortPendingJobs]);

  /**
   * Stops the current run, marking whatever had not finished as cancelled.
   *
   * The documents that already reached Data are left untouched; the ones that
   * were still pending can no longer be attached from this run, so they are
   * reported as cancelled instead of silently disappearing.
   */
  const abort = useCallback(() => {
    runIdRef.current += 1;
    abortPendingJobs();
    runningRef.current = false;
    readyIdsRef.current.clear();
    if (!mountedRef.current) return;

    const cancellation = { code: FAILURE_CODE.CANCELLED, detail: "" };
    const cancelledItems = progressRef.current.items.filter(
      (item) => !TERMINAL_FILE_STATUSES.includes(item.status),
    );
    if (cancelledItems.length > 0) {
      setProgress((previous) => ({
        ...previous,
        items: previous.items.map((item) =>
          TERMINAL_FILE_STATUSES.includes(item.status)
            ? item
            : { ...item, status: FILE_STATUS.ERROR, failure: cancellation },
        ),
      }));
      setFailures((previous) => [
        ...previous,
        ...cancelledItems.map((item) => ({ name: item.name, ...cancellation })),
      ]);
    }
    setPhase(UPLOAD_PHASE.DONE);
    setBusy(false);
  }, [abortPendingJobs]);

  const reset = useCallback(() => {
    abort();
    readyIdsRef.current.clear();
    if (!mountedRef.current) return;
    setPhase(UPLOAD_PHASE.SELECTING);
    setProgress(EMPTY_PROGRESS);
    setFailures([]);
    setSkipped([]);
    setBusy(false);
    setAttach(EMPTY_ATTACH);
    setResolvedFolderName(null);
    setRenamedCount(0);
  }, [abort]);

  /**
   * Creates the batch, retrying once against fresh data after a name conflict.
   *
   * @param {object} params - Batch inputs.
   * @returns {Promise<{payload: object, result: object}>} The sent payload and
   *   the created folder/documents.
   */
  const createBatchWithRetry = useCallback(
    async ({ mode, folderName, entries, parsers }) => {
      const send = async () => {
        const [documents, folders] = await Promise.all([
          getDocuments(),
          getFolders(),
        ]);
        const payload = buildBatchPayload({
          mode,
          folderName,
          entries,
          parsers,
          documents,
          folders,
        });
        const result = await createDocumentsBatch({
          folder_name: payload.folderName,
          files: payload.files,
        });
        if (!Array.isArray(result.documents)) {
          throw new Error("The documents batch response has no documents.");
        }
        return { payload, result };
      };

      try {
        return await send();
      } catch (error) {
        if (error?.response?.status !== 409) throw error;
        return send();
      }
    },
    [],
  );

  const discardDocuments = useCallback(async (documents) => {
    await Promise.allSettled(
      documents.map((document) => deleteDocument(document.id)),
    );
  }, []);

  const discardBatch = useCallback(
    async (result) => {
      await discardDocuments(result.documents);
      if (result.folder?.id != null) {
        await deleteFolder(result.folder.id).catch(() => {});
      }
    },
    [discardDocuments],
  );

  /**
   * Enqueues every created document sequentially, reporting progress.
   *
   * @param {object} params - Enqueue inputs.
   * @returns {Promise<{jobs: Array, failures: Array, unstarted: Array}>} The
   *   queued jobs, the per-file failures and the documents left unenqueued by
   *   an abort.
   */
  const enqueueAll = useCallback(
    async ({ entries, payload, createdDocuments, isCurrent }) => {
      const byName = indexDocumentsByName(createdDocuments);
      const jobs = [];
      const enqueueFailures = [];
      let completed = 0;

      const stopAt = (fromIndex) => ({
        jobs,
        failures: enqueueFailures,
        unstarted: collectUnstarted({
          entries,
          files: payload.files,
          byName,
          documents: createdDocuments,
          fromIndex,
        }),
      });

      for (let index = 0; index < entries.length; index += 1) {
        if (!isCurrent()) {
          return stopAt(index);
        }

        const entry = entries[index];
        const key = entryKey(entry, index);
        const document = matchDocument(
          byName,
          createdDocuments,
          payload.files[index],
          index,
        );
        completed += 1;

        if (!document) {
          const failure = { code: FAILURE_CODE.BATCH, detail: "" };
          enqueueFailures.push({ name: entry.file.name, ...failure });
          updateItem(key, { status: FILE_STATUS.ERROR, failure });
          updateProgress((previous) => ({ ...previous, completed }));
          continue;
        }

        updateItem(key, { status: FILE_STATUS.UPLOADING, document });
        try {
          const job = await enqueueDocumentJob(
            document.id,
            document.name,
            entry.file,
          );
          jobs.push({ key, document, jobId: job.id });
          if (!isCurrent()) {
            return stopAt(index + 1);
          }
          updateItem(key, { status: FILE_STATUS.QUEUED });
        } catch (error) {
          await deleteDocument(document.id).catch(() => {});
          const failure = {
            code: FAILURE_CODE.ENQUEUE,
            detail: getApiErrorMessage(error, ""),
          };
          enqueueFailures.push({ name: document.name, ...failure });
          if (isCurrent()) {
            updateItem(key, { status: FILE_STATUS.ERROR, failure });
          }
        }
        if (!isCurrent()) {
          return stopAt(index + 1);
        }
        updateProgress((previous) => ({ ...previous, completed }));
      }

      return { jobs, failures: enqueueFailures, unstarted: [] };
    },
    [updateItem, updateProgress],
  );

  /**
   * Waits for every queued job, with a timeout and abort reconciliation.
   *
   * @param {object} params - Wait inputs.
   * @returns {Promise<{ids: Array<number>, failures: Array}>} The finished
   *   document ids and the per-file failures.
   */
  const waitForJobs = useCallback(
    async ({ jobs, isCurrent }) => {
      const pending = pendingJobsRef.current;
      const processingFailures = [];

      const promises = jobs.map(({ key, document, jobId }) =>
        new Promise((resolvePromise) => {
          const entry = { timer: null, resolve: resolvePromise };
          const settle = (result) => {
            if (!pending.has(jobId)) return;
            pending.delete(jobId);
            if (entry.timer != null) clearTimeout(entry.timer);
            stopJobPolling(jobId);
            resolvePromise(result);
          };

          entry.timer = setTimeout(async () => {
            stopJobPolling(jobId);
            const fresh = await getDocument(document.id).catch(() => null);
            const failed = fresh?.status !== DOCUMENT_STATUS.FINISHED;
            settle({
              document,
              failed,
              timedOut: failed && fresh?.status !== DOCUMENT_STATUS.ERROR,
              parseFailed: fresh?.status === DOCUMENT_STATUS.ERROR,
            });
          }, JOB_TIMEOUT_MS);

          pending.set(jobId, entry);
          startJobPolling(
            jobId,
            (job) => settle({ document, job, failed: false }),
            (job) => settle({ document, job, failed: true }),
          );
        }).then((result) => {
          if (result.aborted || !isCurrent()) return null;
          if (!result.failed) {
            readyIdsRef.current.add(document.id);
            updateItem(key, { status: FILE_STATUS.READY });
            return document.id;
          }
          const failure = {
            code: result.parseFailed
              ? FAILURE_CODE.PARSE
              : result.timedOut
                ? FAILURE_CODE.TIMEOUT
                : isCancelledStatus(result.job?.status)
                  ? FAILURE_CODE.CANCELLED
                  : FAILURE_CODE.PARSE,
            detail: "",
          };
          processingFailures.push({ name: document.name, ...failure });
          updateItem(key, { status: FILE_STATUS.ERROR, failure });
          return null;
        }),
      );

      const results = await Promise.allSettled(promises);
      const ids = results
        .filter(
          (result) => result.status === "fulfilled" && result.value != null,
        )
        .map((result) => result.value);
      return { ids, failures: processingFailures };
    },
    [updateItem],
  );

  /**
   * Attaches the finished documents to the session and records the outcome.
   *
   * @param {Array<number>} ids - Finished document ids.
   * @param {Function} [isCurrent] - Whether the run is still the current one.
   * @returns {Promise<boolean>} Whether the attach succeeded.
   */
  const attachFinished = useCallback(
    async (ids, isCurrent = () => mountedRef.current) => {
      if (ids.length === 0 || !onReady) return true;
      if (mountedRef.current) {
        setAttach({ status: ATTACH_STATUS.PENDING, ids, failure: null });
      }
      try {
        const accepted = await onReady(ids);
        if (!isCurrent()) return false;
        if (accepted === false) {
          setAttach({
            status: ATTACH_STATUS.FAILED,
            ids,
            failure: { code: FAILURE_CODE.ATTACH, detail: "" },
          });
          return false;
        }
        setAttach({ status: ATTACH_STATUS.DONE, ids, failure: null });
        return true;
      } catch (error) {
        if (isCurrent()) {
          setAttach({
            status: ATTACH_STATUS.FAILED,
            ids,
            failure: {
              code: FAILURE_CODE.ATTACH,
              detail: getApiErrorMessage(error, ""),
            },
          });
        }
        return false;
      }
    },
    [onReady],
  );

  const retryAttach = useCallback(async () => {
    if (attachNowRef.current || attach.status === ATTACH_STATUS.PENDING) return;
    attachNowRef.current = true;
    try {
      const attached = await attachFinished(attach.ids);
      if (attached) readyIdsRef.current.clear();
    } finally {
      attachNowRef.current = false;
    }
  }, [attach.ids, attach.status, attachFinished]);

  /**
   * Attaches the documents that finished before the dialog is closed.
   *
   * The run is about to be abandoned, so this ignores its run token: the
   * documents are already parsed and waiting in Data, and the explicit close is
   * the only chance to put them in the session without a second trip through
   * "Add from Data".
   *
   * @returns {Promise<void>} Resolves once the attach settles.
   */
  const attachReadyNow = useCallback(async () => {
    if (attachNowRef.current || attach.status === ATTACH_STATUS.PENDING) return;
    const ids = [...readyIdsRef.current];
    if (ids.length === 0) return;
    attachNowRef.current = true;
    readyIdsRef.current.clear();
    try {
      await attachFinished(ids, () => true);
    } finally {
      attachNowRef.current = false;
    }
  }, [attach.status, attachFinished]);

  const start = useCallback(
    async ({ mode, folderName, entries, skipped: skippedEntries, parsers }) => {
      if (entries.length === 0 || runningRef.current) return;

      const runId = runIdRef.current + 1;
      runIdRef.current = runId;
      runningRef.current = true;
      readyIdsRef.current.clear();
      const isCurrent = () => mountedRef.current && runIdRef.current === runId;

      setBusy(true);
      setPhase(UPLOAD_PHASE.UPLOADING);
      setFailures([]);
      setSkipped(skippedEntries);
      setAttach(EMPTY_ATTACH);
      setResolvedFolderName(null);
      setRenamedCount(0);
      setProgress({
        completed: 0,
        total: entries.length,
        items: entries.map((entry, index) => ({
          key: entryKey(entry, index),
          name: entry.file.name,
          relativePath: entry.relativePath,
          status: FILE_STATUS.PENDING,
        })),
      });

      /**
       * Marks the whole selection as failed and ends the run.
       *
       * @param {string} code - The failure code.
       * @param {string} [detail] - Backend explanation, when there is one.
       */
      const failSelection = (code, detail = "") => {
        if (!isCurrent()) return;
        const failure = { code, detail };
        setFailures(
          entries.map((entry) => ({ name: entry.file.name, ...failure })),
        );
        setProgress((previous) => ({
          ...previous,
          completed: previous.total,
          items: previous.items.map((item) => ({
            ...item,
            status: FILE_STATUS.ERROR,
            failure,
          })),
        }));
        setPhase(UPLOAD_PHASE.DONE);
      };

      try {
        if (mode === UPLOAD_MODE.FOLDER && !folderName.trim()) {
          failSelection(FAILURE_CODE.FOLDER_NAME);
          return;
        }
        const missingParser = entries.some(
          (entry) => !parsers[getFileExtension(entry.file.name)],
        );
        if (missingParser) {
          failSelection(FAILURE_CODE.PARSER);
          return;
        }

        const { payload, result } = await createBatchWithRetry({
          mode,
          folderName,
          entries,
          parsers,
        });
        if (!isCurrent()) {
          await discardBatch(result);
          return;
        }
        setResolvedFolderName(payload.folderName);
        setRenamedCount(payload.renamedCount);

        const {
          jobs,
          failures: enqueueFailures,
          unstarted,
        } = await enqueueAll({
          entries,
          payload,
          createdDocuments: result.documents,
          isCurrent,
        });
        if (!isCurrent()) {
          await discardDocuments(unstarted);
          if (jobs.length === 0 && result.folder?.id != null) {
            await deleteFolder(result.folder.id).catch(() => {});
          }
          return;
        }

        if (jobs.length === 0) {
          if (result.folder?.id != null) {
            await deleteFolder(result.folder.id).catch(() => {});
          }
          setFailures(enqueueFailures);
          setPhase(UPLOAD_PHASE.DONE);
          return;
        }

        setPhase(UPLOAD_PHASE.PROCESSING);

        const { ids, failures: processingFailures } = await waitForJobs({
          jobs,
          isCurrent,
        });
        if (!isCurrent()) return;

        setFailures([...enqueueFailures, ...processingFailures]);
        const attached = await attachFinished(ids, isCurrent);
        if (attached) readyIdsRef.current.clear();
        if (!isCurrent()) return;
        setPhase(UPLOAD_PHASE.DONE);
      } catch (error) {
        failSelection(FAILURE_CODE.BATCH, getApiErrorMessage(error, ""));
      } finally {
        if (runIdRef.current === runId) {
          runningRef.current = false;
          if (mountedRef.current) setBusy(false);
        }
      }
    },
    [
      attachFinished,
      createBatchWithRetry,
      discardBatch,
      discardDocuments,
      enqueueAll,
      updateItem,
      waitForJobs,
    ],
  );

  return {
    phase,
    progress,
    failures,
    skipped,
    busy,
    attach,
    resolvedFolderName,
    renamedCount,
    start,
    abort,
    reset,
    retryAttach,
    attachReadyNow,
  };
}
