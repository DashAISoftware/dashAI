import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { useTranslation } from "react-i18next";
import { useDatasets } from "../../hooks/datasets/useDatasets";
import { useSessions } from "../../hooks/models/useSessions";
const ModelsContext = createContext(null);

export const useModels = () => useContext(ModelsContext);

export function ModelsProvider({ children }) {
  const { t } = useTranslation(["models", "datasets", "common"]);

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
    enrichDatasetsWithInfo,
    replaceDatasets,
    startDatasetPolling,
  } = useDatasets({ t });

  const {
    tasks,
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
  } = useSessions({ t });

  const [selectedModel, setSelectedModel] = useState(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [step, setStep] = useState(0);

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
  }, [t]);

  const value = {
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
    enrichDatasetsWithInfo,
    replaceDatasets,
    startDatasetPolling,
    tasks,
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
  };

  return (
    <ModelsContext.Provider value={value}>{children}</ModelsContext.Provider>
  );
}
