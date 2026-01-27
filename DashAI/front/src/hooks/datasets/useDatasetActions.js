export function useDatasetActions({
  selectedDatasetId,
  selectedNotebookId,

  selectDataset,
  selectNotebook,
  clearSelectedDataset,
  clearSelectedNotebook,

  deleteDatasetLocal,
  deleteDatasetRemote,
  removeNotebooksByDatasetId,
  deleteNotebookById,

  editDataset,
  editNotebook,

  resetUI,
  selectDatasetView,
  selectNotebookView,
}) {
  const handleDatasetClick = (id) => {
    selectDataset(id);
    clearSelectedNotebook();
    selectDatasetView();
  };

  const handleNotebookClick = (id) => {
    selectNotebook(id);
    clearSelectedDataset();
    selectNotebookView();
  };

  const handleDatasetDelete = async (id) => {
    if (id === selectedDatasetId) {
      clearSelectedDataset();
      resetUI();
    }

    deleteDatasetLocal(id);
    removeNotebooksByDatasetId(id);
    await deleteDatasetRemote(id);
  };

  const handleNotebookDelete = (id) => {
    deleteNotebookById(id);

    if (id === selectedNotebookId) {
      clearSelectedNotebook();
      resetUI();
    }
  };

  return {
    handleDatasetClick,
    handleNotebookClick,
    handleDatasetDelete,
    handleNotebookDelete,
    handleEditDataset: editDataset,
    handleEditNotebook: editNotebook,
  };
}
