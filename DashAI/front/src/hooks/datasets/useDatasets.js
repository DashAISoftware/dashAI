import { useState, useCallback } from "react";
import { useSnackbar } from "notistack";
import {
  getDatasets,
  deleteDataset,
  getDatasetInfo,
  updateDataset,
  createDataset,
} from "../../api/datasets";
import { startJobPolling } from "../../utils/jobPoller";

export function useDatasets({ t }) {
  const { enqueueSnackbar } = useSnackbar();
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);

  // ---------------- helpers ----------------

  const enrichDatasetsWithInfo = useCallback(
    async (newDatasets, existingDatasets = []) => {
      return Promise.all(
        newDatasets.map(async (dataset) => {
          const existing = existingDatasets.find((d) => d.id === dataset.id);

          if (existing) {
            return {
              ...dataset,
              total_rows: existing.total_rows,
              total_columns: existing.total_columns,
            };
          }

          try {
            const info = await getDatasetInfo(dataset.id);
            return {
              ...dataset,
              total_rows: info.total_rows,
              total_columns: info.total_columns,
            };
          } catch (error) {
            console.warn(
              `Failed to fetch info for dataset ${dataset.id}`,
              error,
            );
            return dataset;
          }
        }),
      );
    },
    [],
  );

  // ---------------- actions ----------------

  const fetchDatasets = useCallback(async () => {
    const data = await getDatasets();
    const enriched = await enrichDatasetsWithInfo(data, datasets);
    setDatasets(enriched);
  }, [datasets, enrichDatasetsWithInfo]);

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
        enqueueSnackbar(
          t("datasets:message.datasetCreationSuccess", {
            datasetName: newDataset.name,
          }),
          { variant: "success" },
        );
        await fetchDatasets();
        setSelectedDatasetId(newDataset.id);
      },
      async () => {
        enqueueSnackbar(t("datasets:error.failedToCreateDataset"), {
          variant: "error",
        });
        setDatasets((prev) => prev.filter((d) => d.id !== newDataset.id));
        if (newDataset.id === selectedDatasetId) {
          setSelectedDatasetId(null);
        }
      },
    );
  };

  const replaceDatasets = (datasets) => {
    setDatasets(datasets);
  };

  return {
    datasets,
    selectedDatasetId,
    enrichDatasetsWithInfo,
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
