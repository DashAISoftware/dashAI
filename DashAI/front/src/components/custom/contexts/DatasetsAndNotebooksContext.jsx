import { createContext, useContext, useEffect, useState } from "react";

import { useTranslation } from "react-i18next";
import { useDatasets } from "../../../hooks/datasets/useDatasets";
import { useNotebooks } from "../../../hooks/datasets/useNotebooks";
import { create } from "yup/lib/Reference";

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
    deleteDatasetLocal,
    deleteDatasetRemote,
    editDataset,
    addDatasetOptimistically,
    enrichDatasetsWithInfo,
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

  useEffect(() => {
    fetchDatasets();
    fetchNotebooks();
  }, []);

  const value = {
    datasets,
    createDataset,
    selectedDatasetId,
    fetchDatasets,
    selectDataset,
    clearSelectedDataset,
    deleteDatasetLocal,
    deleteDatasetRemote,
    editDataset,
    addDatasetOptimistically,
    enrichDatasetsWithInfo,
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
  };

  return (
    <DatasetsAndNotebooksContext.Provider value={value}>
      {children}
    </DatasetsAndNotebooksContext.Provider>
  );
};
