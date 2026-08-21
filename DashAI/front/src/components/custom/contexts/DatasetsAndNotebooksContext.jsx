import { createContext, useContext, useEffect, useState } from "react";

import { useTranslation } from "react-i18next";
import { useDatasets } from "../../../hooks/datasets/useDatasets";
import { useFolders } from "../../../hooks/datasets/useFolders";
import { useNotebooks } from "../../../hooks/datasets/useNotebooks";
import { useDownloads } from "../../../hooks/datasets/useDownloads";

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
    deleteDatasetsByIds,
    editDataset,
    moveDatasetToFolder,
    addDatasetOptimistically,
    replaceDatasets,
    startDatasetPolling,
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
    downloads,
    fetchDownloads,
    deleteDownloadById,
    updateDownload,
    addDownload,
  } = useDownloads();

  const {
    notebooks,
    selectedNotebookId,
    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    deleteNotebookById,
    deleteNotebooksByIds,
    editNotebook,
    addNotebookOptimistically,
    removeNotebooksByDatasetId,
  } = useNotebooks({ t });

  // Derived once from the URL present at mount so a direct navigation to
  // .../datasets/new (or .../notebooks/new) renders the right step on the
  // very first paint, instead of flashing the default "new" landing menu
  // for a frame while DatasetsContent's location-sync effect catches up.
  const initialPath =
    typeof window !== "undefined" ? window.location.pathname : "";
  const initialSelectedOption = initialPath.startsWith(
    "/app/data/notebooks/new",
  )
    ? OptionsEnum.NOTEBOOK
    : initialPath.startsWith("/app/data/datasets/new")
      ? OptionsEnum.DATASET
      : OptionsEnum.NEW;
  const initialStep = initialSelectedOption === OptionsEnum.NEW ? 0 : 1;

  const [step, setStep] = useState(initialStep);
  const [selectedOption, setSelectedOption] = useState(initialSelectedOption); // "datasets" or "notebooks"

  const [rightBarContent, setRightBarContent] = useState(null);
  const [availableConverters, setAvailableConverters] = useState([]);
  const [availableExplorers, setAvailableExplorers] = useState([]);
  const [uploadDataloader, setUploadDataloader] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [datasetTab, setDatasetTab] = useState(0);
  const [scrollToColumn, setScrollToColumn] = useState(null);

  useEffect(() => {
    fetchNotebooks();
  }, []);

  const value = {
    downloads,
    fetchDownloads,
    deleteDownloadById,
    updateDownload,
    addDownload,
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
    moveDatasetToFolder,
    addDatasetOptimistically,
    replaceDatasets,
    startDatasetPolling,
    folders,
    fetchFolders,
    createFolder,
    renameFolder,
    deleteFolderById,
    notebooks,
    selectedNotebookId,
    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    deleteNotebookById,
    deleteNotebooksByIds,
    editNotebook,
    addNotebookOptimistically,
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
    scrollToColumn,
    setScrollToColumn,
    uploadDataloader,
    setUploadDataloader,
  };

  return (
    <DatasetsAndNotebooksContext.Provider value={value}>
      {children}
    </DatasetsAndNotebooksContext.Provider>
  );
};
