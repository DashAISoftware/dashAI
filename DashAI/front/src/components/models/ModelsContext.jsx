import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
} from "react";
import { useTranslation } from "react-i18next";
import { useDatasets } from "../../hooks/datasets/useDatasets";
import { useFolders } from "../../hooks/datasets/useFolders";
import { useSessions } from "../../hooks/models/useSessions";
const ModelsContext = createContext(null);

export const useModels = () => useContext(ModelsContext);

export const OptionsEnum = Object.freeze({
  DATASET: "dataset",
  SESSION: "session",
  NEW: "new",
});

export function ModelsProvider({ children }) {
  const { t, i18n } = useTranslation(["models", "datasets", "common"]);

  const {
    datasets,
    createDataset,
    selectedDatasetId,
    fetchDatasets,
    selectDataset,
    clearSelectedDataset,
    deleteDataset,
    deleteDatasetById,
    editDataset,
    addDatasetOptimistically,
    replaceDatasets,
    startDatasetPolling,
    moveDatasetToFolder,
  } = useDatasets({ t });

  const {
    folders,
    fetchFolders,
    createFolder,
    renameFolder,
    deleteFolderById,
  } = useFolders({ t });

  const {
    tasks,
    loadingTasks,
    selectedTask,
    selectedSessionId,
    selectedSession,
    sessions,
    setSessions,
    fetchSessions,
    fetchTasks,
    editSession,
    deleteSessionById,
    setSelectedTask,
    setSelectedSessionId,
    setSelectedSession,
    runs,
    setRuns,
    retrainDialogOpen,
    setRetrainDialogOpen,
    runToRetrain,
    setRunToRetrain,
    operationsCount,
    setOperationsCount,
    fetchRuns,
    executeTraining,
    onRunCreated,
    onTrainRun,
    onDeleteRun,
    onEditRun,
    handleCancelRetrain,
    handleConfirmRetrain,
    lastAddedRunId,
    clearLastAddedRunId,
  } = useSessions({ t });

  const [selectedModel, setSelectedModel] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [activeRunId, setActiveRunId] = useState(null);
  const [selectedOption, setSelectedOption] = useState(OptionsEnum.NEW);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [datasetTab, setDatasetTab] = useState(0);
  const [sessionRightContent, setSessionRightContent] = useState(null);
  const [runDetailTab, setRunDetailTab] = useState(null);
  const [explainerRefreshTrigger, setExplainerRefreshTrigger] = useState(0);
  const [explainerToCreate, setExplainerToCreate] = useState(null);

  const triggerExplainerRefresh = useCallback(() => {
    setExplainerRefreshTrigger((prev) => prev + 1);
  }, []);

  // Open the explainer creation dialog for a given {scope, name}. Shared so both
  // the sidebar (click) and the central view (drag and drop) can trigger it,
  // mirroring how selectModel opens the add model dialog.
  const openExplainerCreator = useCallback((explainer) => {
    setExplainerToCreate(explainer);
  }, []);

  const closeExplainerCreator = useCallback(() => {
    setExplainerToCreate(null);
  }, []);

  const selectModel = useCallback((model) => {
    setSelectedModel(model);
    setConfigOpen(true);
  }, []);

  const closeConfig = useCallback(() => {
    setConfigOpen(false);
    setSelectedModel(null);
  }, []);

  useEffect(() => {
    fetchDatasets();
    fetchSessions();
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [i18n.language]);

  // Memoized — this context wraps the entire models page tree, so a fresh
  // object literal every render would force every consumer (RunCard,
  // ModelDetailView, ModelsRightBar, ...) to re-render whenever ANY field
  // here changed, not just the one(s) a given consumer actually reads.
  const value = useMemo(
    () => ({
      selectedModel,
      configOpen,
      selectModel,
      closeConfig,
      setSelectedModel,
      setConfigOpen,
      datasets,
      createDataset,
      selectedDatasetId,
      fetchDatasets,
      selectDataset,
      clearSelectedDataset,
      deleteDataset,
      deleteDatasetById,
      editDataset,
      addDatasetOptimistically,
      replaceDatasets,
      startDatasetPolling,
      moveDatasetToFolder,
      folders,
      fetchFolders,
      createFolder,
      renameFolder,
      deleteFolderById,
      tasks,
      loadingTasks,
      selectedTask,
      selectedSessionId,
      selectedSession,
      sessions,
      setSessions,
      fetchSessions,
      fetchTasks,
      editSession,
      deleteSessionById,
      setSelectedTask,
      setSelectedSessionId,
      setSelectedSession,
      step,
      setStep,
      activeRunId,
      setActiveRunId,
      runs,
      setRuns,
      retrainDialogOpen,
      setRetrainDialogOpen,
      runToRetrain,
      setRunToRetrain,
      operationsCount,
      setOperationsCount,
      fetchRuns,
      executeTraining,
      onRunCreated,
      onTrainRun,
      onEditRun,
      onDeleteRun,
      handleCancelRetrain,
      handleConfirmRetrain,
      lastAddedRunId,
      clearLastAddedRunId,
      datasetInfo,
      setDatasetInfo,
      datasetTab,
      setDatasetTab,
      sessionRightContent,
      setSessionRightContent,
      runDetailTab,
      setRunDetailTab,
      explainerRefreshTrigger,
      triggerExplainerRefresh,
      explainerToCreate,
      openExplainerCreator,
      closeExplainerCreator,
    }),
    [
      selectedModel,
      configOpen,
      selectModel,
      closeConfig,
      datasets,
      createDataset,
      selectedDatasetId,
      fetchDatasets,
      selectDataset,
      clearSelectedDataset,
      deleteDataset,
      deleteDatasetById,
      editDataset,
      addDatasetOptimistically,
      replaceDatasets,
      startDatasetPolling,
      moveDatasetToFolder,
      folders,
      fetchFolders,
      createFolder,
      renameFolder,
      deleteFolderById,
      tasks,
      loadingTasks,
      selectedTask,
      selectedSessionId,
      selectedSession,
      sessions,
      fetchSessions,
      fetchTasks,
      editSession,
      deleteSessionById,
      step,
      activeRunId,
      runs,
      retrainDialogOpen,
      runToRetrain,
      operationsCount,
      fetchRuns,
      executeTraining,
      onRunCreated,
      onTrainRun,
      onEditRun,
      onDeleteRun,
      handleCancelRetrain,
      handleConfirmRetrain,
      lastAddedRunId,
      clearLastAddedRunId,
      datasetInfo,
      datasetTab,
      sessionRightContent,
      runDetailTab,
      explainerRefreshTrigger,
      triggerExplainerRefresh,
      explainerToCreate,
      openExplainerCreator,
      closeExplainerCreator,
    ],
  );

  return (
    <ModelsContext.Provider value={value}>{children}</ModelsContext.Provider>
  );
}
