import { useState, useCallback } from "react";
import { getNotebooks, deleteNotebook, updateNotebook } from "../api/notebook";

export function useNotebooks({ enqueueSnackbar, t }) {
  const [notebooks, setNotebooks] = useState([]);
  const [selectedNotebookId, setSelectedNotebookId] = useState(null);

  // -------- actions --------

  const fetchNotebooks = useCallback(async () => {
    try {
      const data = await getNotebooks();
      setNotebooks(data);
    } catch (error) {
      enqueueSnackbar(t("datasets:error.failedToFetchNotebooks"), {
        variant: "error",
      });
      console.error("Failed to fetch notebooks:", error);
    }
  }, [enqueueSnackbar, t]);

  const selectNotebook = (id) => {
    setSelectedNotebookId(id);
  };

  const clearSelectedNotebook = () => {
    setSelectedNotebookId(null);
  };

  const deleteNotebookById = async (id) => {
    setNotebooks((prev) => prev.filter((n) => n.id !== id));
    await deleteNotebook(id);
  };

  const editNotebook = async (id, newName) => {
    try {
      const updated = await updateNotebook(id, { name: newName });
      setNotebooks((prev) =>
        prev.map((n) => (n.id === id ? { ...n, name: updated.name } : n)),
      );
      enqueueSnackbar(t("datasets:message.notebookUpdateSuccess"), {
        variant: "success",
      });
    } catch (error) {
      if (error.response?.status === 422) {
        enqueueSnackbar(t("datasets:error.notebookNameEmpty"), {
          variant: "error",
        });
      } else if (error.response?.status === 304) {
        enqueueSnackbar(t("datasets:message.noChangesMade"), {
          variant: "info",
        });
      } else {
        enqueueSnackbar(t("datasets:error.failedToUpdateNotebook"), {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const removeNotebooksByDatasetId = (datasetId) => {
    setNotebooks((prev) => prev.filter((n) => n.dataset_id !== datasetId));

    if (
      selectedNotebookId &&
      notebooks.find(
        (n) => n.id === selectedNotebookId && n.dataset_id === datasetId,
      )
    ) {
      setSelectedNotebookId(null);
    }
  };

  return {
    notebooks,
    selectedNotebookId,

    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    deleteNotebookById,
    editNotebook,

    removeNotebooksByDatasetId,
  };
}
