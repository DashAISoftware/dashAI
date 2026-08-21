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
import { useModelComponents } from "../../hooks/models/useModelComponents";
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
    deleteDatasetsByIds,
    editDataset,
    addDatasetOptimistically,
    replaceDatasets,
    startDatasetPolling,
    moveDatasetToFolder,
    datasetRowCount,
    setDatasetRowCount,
  } = useDatasets({ t });

  const {
    folders,
    fetchFolders,
    createFolder,
    renameFolder,
    deleteFolderById: deleteFolderByIdRaw,
  } = useFolders({ t });

  // Deleting a folder moves its datasets to "no folder" server-side
  // (folder_id set to null via the FK's ON DELETE SET NULL), but the local
  // `datasets` state still holds the old folder_id until this clears it —
  // otherwise those datasets vanish from the list until a full refetch.
  const deleteFolderById = async (id) => {
    const success = await deleteFolderByIdRaw(id);
    if (success) {
      replaceDatasets((prev) =>
        prev.map((d) => (d.folder_id === id ? { ...d, folder_id: null } : d)),
      );
    }
    return success;
  };

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
    deleteSessionsByIds,
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

  const { allModels, allMetrics, getModelsForTask } = useModelComponents({
    language: i18n.language,
  });

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
  const [selectedStatisticalTest, setSelectedStatisticalTest] = useState(null);
  const [statisticalTestsModalOpen, setStatisticalTestsModalOpen] =
    useState(false);

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

  const openStatisticalTest = useCallback((test) => {
    setSelectedStatisticalTest(test);
    setStatisticalTestsModalOpen(true);
  }, []);

  const closeStatisticalTest = useCallback(() => {
    setSelectedStatisticalTest(null);
    setStatisticalTestsModalOpen(false);
  }, []);

  useEffect(() => {
    fetchDatasets();
    fetchSessions();
  }, []);

  // Poll while the selected session's converters are still being
  // fit/transformed (see SessionPreprocessingJob) — refreshing the whole
  // session list is enough, since ModelsContent re-derives `selectedSession`
  // from it. No-op for sessions without converters (status never changes).
  useEffect(() => {
    if (!selectedSession) return;
    const hasConverters = (selectedSession.converters || []).length > 0;
    const isPending =
      hasConverters &&
      selectedSession.preprocessing_status !== 3 &&
      selectedSession.preprocessing_status !== 4;
    if (!isPending) return;

    const interval = setInterval(() => {
      fetchSessions();
    }, 2000);
    return () => clearInterval(interval);
  }, [
    selectedSession?.id,
    selectedSession?.preprocessing_status,
    selectedSession?.converters,
    fetchSessions,
  ]);

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
      deleteDatasetsByIds,
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
      deleteSessionsByIds,
      setSelectedTask,
      setSelectedSessionId,
      setSelectedSession,
      allModels,
      allMetrics,
      getModelsForTask,
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
      datasetRowCount,
      setDatasetRowCount,
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
      selectedStatisticalTest,
      statisticalTestsModalOpen,
      openStatisticalTest,
      closeStatisticalTest,
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
      deleteDatasetsByIds,
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
      deleteSessionsByIds,
      allModels,
      allMetrics,
      getModelsForTask,
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
      datasetRowCount,
      datasetTab,
      sessionRightContent,
      runDetailTab,
      explainerRefreshTrigger,
      triggerExplainerRefresh,
      explainerToCreate,
      openExplainerCreator,
      closeExplainerCreator,
      selectedStatisticalTest,
      statisticalTestsModalOpen,
      openStatisticalTest,
      closeStatisticalTest,
    ],
  );

  return (
    <ModelsContext.Provider value={value}>{children}</ModelsContext.Provider>
  );
}
