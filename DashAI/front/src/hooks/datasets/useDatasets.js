import { useState, useCallback, useEffect } from "react";
import { useSnackbar } from "notistack";
import {
  getDatasets,
  deleteDataset,
  updateDataset,
  createDataset,
} from "../../api/datasets";
import { startJobPolling, subscribeJobs } from "../../utils/jobPoller";

export function useDatasets({ t }) {
  const { enqueueSnackbar } = useSnackbar();
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);

  useEffect(() => {
    fetchDatasets();
  }, []);

  // ---------------- actions ----------------

  const fetchDatasets = useCallback(async () => {
    const data = await getDatasets();
    setDatasets(data);
    return data;
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeJobs((jobs) => {
      const datasetJobs = Array.isArray(jobs)
        ? jobs.filter((job) => job.task_type === "DatasetJob")
        : [];
      if (datasetJobs.length > 0) {
        fetchDatasets();
      }
    });

    return unsubscribe;
  }, [fetchDatasets]);

  const selectDataset = (id) => {
    setSelectedDatasetId(id);
  };

  const clearSelectedDataset = () => {
    setSelectedDatasetId(null);
  };

  const deleteDatasetById = async (id) => {
    try {
      await deleteDataset(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
      if (id === selectedDatasetId) {
        setSelectedDatasetId(null);
      }
      return true;
    } catch (error) {
      enqueueSnackbar(t("datasets:error.failedToDeleteDataset"), {
        variant: "error",
      });
      console.error("Error deleting dataset:", error);
    }
    return false;
  };

  const editDataset = async (id, newName) => {
    try {
      const updated = await updateDataset(id, { name: newName });
      setDatasets((prev) =>
        prev.map((d) => (d.id === id ? { ...d, name: updated.name } : d)),
      );
      enqueueSnackbar(t("datasets:message.datasetUpdateSuccess"), {
        variant: "success",
      });
    } catch (error) {
      if (error.response?.status === 409) {
        enqueueSnackbar(t("datasets:error.datasetNameExists"), {
          variant: "error",
        });
      } else if (error.response?.status === 422) {
        enqueueSnackbar(t("datasets:error.datasetNameEmpty"), {
          variant: "error",
        });
      } else {
        enqueueSnackbar(t("datasets:error.failedToUpdateDataset"), {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const addDatasetOptimistically = (dataset) => {
    setDatasets((prev) => [...prev, dataset]);
    setSelectedDatasetId(dataset.id);
  };

  const startDatasetPolling = (newDataset, datasetJob) => {
    startJobPolling(
      datasetJob.id,
      async () => {
        await fetchDatasets();

        enqueueSnackbar(
          t("datasets:message.datasetCreationSuccess", {
            datasetName: newDataset.name,
          }),
          { variant: "success" },
        );
        setSelectedDatasetId(newDataset.id);
      },
      async () => {
        enqueueSnackbar(t("datasets:error.failedToCreateDataset"), {
          variant: "error",
        });
        setDatasets((prev) => prev.filter((d) => d.id !== newDataset.id));
      },
    );
  };

  const replaceDatasets = (datasets) => {
    setDatasets(datasets);
  };

  return {
    datasets,
    selectedDatasetId,
    createDataset,
    fetchDatasets,
    selectDataset,
    clearSelectedDataset,
    deleteDataset,
    deleteDatasetById,
    editDataset,
    addDatasetOptimistically,
    startDatasetPolling,
    replaceDatasets,
  };
}
