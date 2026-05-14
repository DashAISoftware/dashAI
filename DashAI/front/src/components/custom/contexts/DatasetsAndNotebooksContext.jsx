import { createContext, useContext, useEffect, useState } from "react";

import { useTranslation } from "react-i18next";
import { useDatasets } from "../../../hooks/datasets/useDatasets";
import { useNotebooks } from "../../../hooks/datasets/useNotebooks";

const DatasetsAndNotebooksContext = createContext();

export const useDatasetsAndNotebooks = () =>
  useContext(DatasetsAndNotebooksContext);

export const OptionsEnum = Object.freeze({
  DATASET: "dataset",
  NOTEBOOK: "notebook",
  NEW: "new",
});

export const DatasetsAndNotebooksProvider = ({ children }) => {
  const { t } = useTranslation(["datasets", "common"]);
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
  } = useDatasets({ t });

  const {
    notebooks,
    selectedNotebookId,
    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    deleteNotebookById,
    editNotebook,
    removeNotebooksByDatasetId,
  } = useNotebooks({ t });

  const [step, setStep] = useState(0);
  const [selectedOption, setSelectedOption] = useState(OptionsEnum.NEW); // "datasets" or "notebooks"

  const [rightBarContent, setRightBarContent] = useState(null);
  const [uploadDataloader, setUploadDataloader] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [datasetTab, setDatasetTab] = useState(0);

  useEffect(() => {
    fetchNotebooks();
  }, []);

  const value = {
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
    notebooks,
    selectedNotebookId,
    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    deleteNotebookById,
    editNotebook,
    removeNotebooksByDatasetId,
    selectedOption,
    setSelectedOption,
    step,
    setStep,
    rightBarContent,
    setRightBarContent,
    datasetInfo,
    setDatasetInfo,
    datasetTab,
    setDatasetTab,
    uploadDataloader,
    setUploadDataloader,
  };

  return (
    <DatasetsAndNotebooksContext.Provider value={value}>
      {children}
    </DatasetsAndNotebooksContext.Provider>
  );
};
