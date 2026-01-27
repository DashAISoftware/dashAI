export function useNotebookActions({
  fetchNotebooks,
  selectNotebook,
  clearSelectedNotebook,
  clearSelectedDataset,
  selectNotebookView,
  selectDatasetView,
  goToNotebookCreation,
  createDatasetFromNotebook,
}) {
  const handleAddDatasetFromNotebook = async (name, selectedNotebook) => {
    if (!selectedNotebook) return;

    clearSelectedNotebook();
    selectDatasetView();

    createDatasetFromNotebook(name, selectedNotebook.id);
  };

  const handleNotebookCreated = async (createdNotebook) => {
    await fetchNotebooks();
    selectNotebookView();
    selectNotebook(createdNotebook.id);
    clearSelectedDataset();
  };

  const handleNewNotebookFromDataset = () => {
    goToNotebookCreation();
  };

  return {
    handleAddDatasetFromNotebook,
    handleNotebookCreated,
    handleNewNotebookFromDataset,
  };
}
