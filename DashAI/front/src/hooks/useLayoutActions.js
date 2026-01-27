export function useLayoutActions({
  goToDatasetFlow,
  goToNotebookFlow,
  resetUI,

  clearSelectedDataset,
  clearSelectedNotebook,

  selectDatasetView,

  addDatasetOptimistically,
  startDatasetPolling,

  setRightBarContent,
  tourContext,
}) {
  const goToNextStep = (option) => {
    if (option === "dataset") {
      goToDatasetFlow();
    } else {
      goToNotebookFlow();
    }

    clearSelectedDataset();
    clearSelectedNotebook();

    if (option === "dataset" && tourContext?.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 600);
    }
  };

  const handleNewSessionButton = () => {
    clearSelectedDataset();
    clearSelectedNotebook();
    resetUI();
  };

  const handleDatasetCreated = (newDataset, datasetJob) => {
    addDatasetOptimistically(newDataset);
    selectDatasetView();
    clearSelectedNotebook();
    setRightBarContent(null);
    startDatasetPolling(newDataset, datasetJob);
  };

  return {
    goToNextStep,
    handleNewSessionButton,
    handleDatasetCreated,
  };
}
