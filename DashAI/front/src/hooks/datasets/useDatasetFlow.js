import { startJobPolling } from "../../utils/jobPoller";
import { enqueueDatasetJob } from "../../api/job";
import { createDataset, deleteDataset } from "../../api/datasets";
import { useSnackbar } from "notistack";

export function useDatasetFlow({
  datasets,
  enrichDatasetsWithInfo,
  fetchDatasets,
  replaceDatasets,
  addDatasetOptimistically,
  selectDataset,
  clearSelectedDataset,
  t,
  resetUI,
  deleteDatasetRemote,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const pollForDataset = ({ datasetId, datasetName }, { jobId }) => {
    if (!jobId) return;

    startJobPolling(
      jobId,

      //Susccess
      async () => {
        enqueueSnackbar(
          t("datasets:message.datasetCreationSuccess", { datasetName }),
          { variant: "success" },
        );

        try {
          const freshDatasets = await fetchDatasets(true);
          const dataset = freshDatasets.find((d) => d.id === datasetId);

          if (dataset) {
            const enriched = await enrichDatasetsWithInfo(
              freshDatasets,
              datasets,
            );
            replaceDatasets(enriched);
            selectDataset(datasetId);
          } else {
            await fetchDatasets();
            selectDataset(datasetId);
          }
        } catch (error) {
          console.error("Error after dataset job completion:", error);
          await fetchDatasets();
          selectDataset(datasetId);
        }
      },

      //Failure
      async (result) => {
        console.error("Dataset job failed:", result);

        enqueueSnackbar(
          t("datasets:error.failedToCreateDataset", {
            error: result?.error || t("common:unknownError"),
          }),
          { variant: "error" },
        );

        deleteDatasetRemote(datasetId).catch(console.error);
        clearSelectedDataset();
        resetUI();
      },
    );
  };

  const createDatasetFromNotebook = async (name, notebookId) => {
    try {
      console.log(
        "Creating dataset from notebook:",
        notebookId,
        "with name:",
        name,
      );
      const dataset = await createDataset(name);

      enqueueSnackbar(t("datasets:message.datasetCreationStarted"), {
        variant: "success",
      });

      // optimistic
      replaceDatasets((prev) => [...prev, dataset]);
      selectDataset(dataset.id);

      const job = await enqueueDatasetJob(dataset.id, null, "", {}, notebookId);

      pollForDataset(
        { datasetId: dataset.id, datasetName: name },
        { jobId: job.id },
      );
    } catch (error) {
      enqueueSnackbar(t("datasets:error.failedToCreateDatasetFromNotebook"), {
        variant: "error",
      });
      console.error("Failed to create dataset from notebook:", error);
    }
  };

  const createDatasetFromUpload = (dataset, job) => {
    addDatasetOptimistically(dataset);
    selectDataset(dataset.id);
    pollForDataset(
      { datasetId: dataset.id, datasetName: dataset.name },
      { jobId: job.id },
    );
  };

  return {
    createDatasetFromNotebook,
    createDatasetFromUpload,
    pollForDataset,
  };
}
