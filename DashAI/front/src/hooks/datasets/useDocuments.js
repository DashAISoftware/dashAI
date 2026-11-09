import { useCallback, useEffect, useRef, useState } from "react";
import { useSnackbar } from "notistack";
import {
  deleteDocument,
  getDocument,
  getDocuments,
  updateDocument,
} from "../../api/documents";
import {
  startJobPolling,
  subscribeJobs,
  TERMINAL_JOB_STATUSES,
} from "../../utils/jobPoller";

/** Window that groups the terminal DocumentJob events of a large upload. */
const DOCUMENT_REFRESH_DEBOUNCE_MS = 500;

export const DOCUMENT_STATUS = Object.freeze({
  NOT_STARTED: 0,
  DELIVERED: 1,
  STARTED: 2,
  FINISHED: 3,
  ERROR: 4,
});

export function useDocuments({ t }) {
  const { enqueueSnackbar } = useSnackbar();
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const fetchRequestRef = useRef(0);

  const fetchDocuments = useCallback(async () => {
    const requestId = fetchRequestRef.current + 1;
    fetchRequestRef.current = requestId;
    try {
      const data = await getDocuments();
      if (requestId === fetchRequestRef.current) setDocuments(data);
      return data;
    } catch (error) {
      console.error("Error fetching documents:", error);
      return [];
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    let refreshTimer = null;
    let refreshPending = false;

    const unsubscribe = subscribeJobs((jobs) => {
      if (!Array.isArray(jobs)) return;
      const finishedDocument = jobs.some(
        (job) =>
          job.task_type === "DocumentJob" &&
          TERMINAL_JOB_STATUSES.includes(job.status),
      );
      if (!finishedDocument) return;

      // The first event of a burst refreshes immediately; the rest are folded
      // into one trailing refresh so a 300-file upload does not fire 300 GETs.
      if (refreshTimer == null) {
        fetchDocuments();
        refreshTimer = setTimeout(() => {
          refreshTimer = null;
          if (!refreshPending) return;
          refreshPending = false;
          fetchDocuments();
        }, DOCUMENT_REFRESH_DEBOUNCE_MS);
        return;
      }
      refreshPending = true;
    });

    return () => {
      unsubscribe();
      if (refreshTimer != null) clearTimeout(refreshTimer);
    };
  }, [fetchDocuments]);

  const selectDocument = useCallback((id) => setSelectedDocumentId(id), []);
  const clearSelectedDocument = useCallback(
    () => setSelectedDocumentId(null),
    [],
  );

  const refreshDocument = async (id) => {
    try {
      const fresh = await getDocument(id);
      setDocuments((prev) => prev.map((d) => (d.id === id ? fresh : d)));
      return fresh;
    } catch (error) {
      return null;
    }
  };

  const deleteDocumentById = async (id) => {
    try {
      await deleteDocument(id);
    } catch (error) {
      const usedBy = error.response?.data?.detail?.sessions;
      if (error.response?.status === 409 && Array.isArray(usedBy)) {
        enqueueSnackbar(
          t("datasets:error.documentInUse", {
            sessions: usedBy.map((session) => session.name).join(", "),
          }),
          { variant: "warning" },
        );
        return false;
      }
      if (error.response?.status !== 404) {
        const key =
          error.response?.status === 409
            ? "datasets:document.deleteWhileParsing"
            : "datasets:document.failedToDelete";
        enqueueSnackbar(t(key), { variant: "error" });
        return false;
      }
    }
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    setSelectedDocumentId((prev) => (prev === id ? null : prev));
    return true;
  };

  const editDocument = async (id, newName) => {
    try {
      const updated = await updateDocument(id, { name: newName });
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, name: updated.name } : d)),
      );
    } catch (error) {
      const key =
        error.response?.status === 409
          ? "datasets:document.nameExists"
          : "datasets:document.failedToUpdate";
      enqueueSnackbar(t(key), { variant: "error" });
      throw error;
    }
  };

  const moveDocumentToFolder = async (id, folderId) => {
    const previous = documents.find((d) => d.id === id);
    setDocuments((prev) =>
      prev.map((d) => (d.id === id ? { ...d, folder_id: folderId } : d)),
    );
    try {
      await updateDocument(id, { folder_id: folderId });
    } catch (error) {
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === id ? { ...d, folder_id: previous?.folder_id ?? null } : d,
        ),
      );
      enqueueSnackbar(t("datasets:document.failedToUpdate"), {
        variant: "error",
      });
    }
  };

  const addDocumentOptimistically = (document) => {
    setDocuments((prev) => [...prev, document]);
    setSelectedDocumentId(document.id);
  };

  const notifyReady = (name) =>
    enqueueSnackbar(t("datasets:document.creationSuccess", { name }), {
      variant: "success",
    });

  const startDocumentPolling = (newDocument, job) => {
    startJobPolling(
      job.id,
      async () => {
        await refreshDocument(newDocument.id);
        notifyReady(newDocument.name);
      },
      async (result) => {
        const fresh = await refreshDocument(newDocument.id);
        if (fresh?.status === DOCUMENT_STATUS.FINISHED) {
          notifyReady(newDocument.name);
          return;
        }
        if (result?.status === "cancelled") {
          enqueueSnackbar(t("common:jobQueue.jobCancelled"), {
            variant: "info",
          });
        } else {
          enqueueSnackbar(t("datasets:document.creationError"), {
            variant: "error",
          });
        }
      },
    );
  };

  return {
    documents,
    selectedDocumentId,
    fetchDocuments,
    selectDocument,
    clearSelectedDocument,
    deleteDocumentById,
    editDocument,
    moveDocumentToFolder,
    addDocumentOptimistically,
    startDocumentPolling,
    refreshDocument,
  };
}
