import { useState, useEffect } from "react";
import { Box } from "@mui/material";
import LeftBar from "../../components/notebooks/LeftBar";
import CenterBox from "../../components/threeSectionLayout/CenterBox";
import RightBar from "../../components/notebooks/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import UploadDatasetSteps from "../../components/notebooks/datasetCreation/UploadDatasetSteps";
import UploadNotebookSteps from "../../components/notebooks/notebookCreation/UploadNotebookSteps";
import DatasetVisualization from "../../components/notebooks/dataset/DatasetVisualization";
import NotebookVisualization from "../../components/notebooks/notebook/NotebookVisualization";
import {
  getDatasets,
  deleteDataset,
  getDatasetInfo,
  updateDataset,
  createDataset,
} from "../../api/datasets";
import { startJobPolling } from "../../utils/jobPoller";
import {
  getNotebooks,
  deleteNotebook,
  updateNotebook,
} from "../../api/notebook";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";

import { enqueueDatasetJob } from "../../api/job";
import { useSnackbar } from "notistack";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { useTourContext } from "../../components/tour/TourProvider";

export default function DatasetsPage() {
  const [step, setStep] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [selectedNotebookId, setSelectedNotebookId] = useState(0);
  const [datasets, setDatasets] = useState([]);
  const [notebooks, setNotebooks] = useState([]);
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();

  const menuOptions = [
    {
      name: "dataset",
      display_name: "Upload Dataset",
      description: "Import your data from various sources and formats.",
      Icon: null,
      "data-tour": "dataset-option",
    },
    {
      name: "notebook",
      display_name: "Create a New Notebook",
      description: "Start a new analysis session with an existing dataset.",
      Icon: null,
      "data-tour": "notebook-option",
    },
  ];

  const goToNextStep = (option) => {
    if (option === "dataset" && tourContext?.run) {
      setStep((prevStep) => prevStep + 1);
      setSelectedOption(option);
      setSelectedNotebookId(null);
      setSelectedDatasetId(null);
      setTimeout(() => {
        tourContext.nextStep();
      }, 600);
    } else {
      setStep((prevStep) => prevStep + 1);
      setSelectedOption(option);
      setSelectedNotebookId(null);
      setSelectedDatasetId(null);
    }
  };

  const enrichDatasetsWithInfo = async (newDatasets, existingDatasets = []) => {
    const enrichedDatasets = await Promise.all(
      newDatasets.map(async (dataset) => {
        const existingDataset = existingDatasets.find(
          (d) => d.id === dataset.id,
        );
        if (
          existingDataset &&
          existingDataset.description &&
          existingDataset.description.includes("rows,")
        ) {
          return {
            ...dataset,
            description: existingDataset.description,
          };
        }

        try {
          const info = await getDatasetInfo(dataset.id);
          return {
            ...dataset,
            description: `${info.total_rows} rows, ${info.total_columns} columns`,
          };
        } catch (error) {
          console.warn(
            `Failed to fetch info for dataset ${dataset.id}:`,
            error,
          );
          return {
            ...dataset,
            description: dataset.description || "",
          };
        }
      }),
    );
    return enrichedDatasets;
  };

  const fetchDatasets = async () => {
    try {
      const data = await getDatasets();
      const enrichedDatasets = await enrichDatasetsWithInfo(data, datasets);
      setDatasets(enrichedDatasets);
    } catch (error) {
      enqueueSnackbar("Failed to fetch datasets", {
        variant: "error",
      });
      console.error("Failed to fetch datasets:", error);
    }
  };

  const fetchNotebooks = async () => {
    try {
      const data = await getNotebooks();
      setNotebooks(data);
    } catch (error) {
      enqueueSnackbar("Failed to fetch notebooks", {
        variant: "error",
      });
      console.error("Failed to fetch notebooks:", error);
    }
  };

  useEffect(() => {
    fetchDatasets();
    fetchNotebooks();
  }, []);

  const handleNewSessionButton = () => {
    setSelectedDatasetId(null);
    setSelectedNotebookId(null);
    setStep(0);
    setSelectedOption(null);
  };

  const handleDatasetClick = (datasetId) => {
    setSelectedDatasetId(datasetId);
    setSelectedNotebookId(null);
    setSelectedOption("dataset");
  };

  const handleNotebookClick = (notebookId) => {
    setSelectedNotebookId(notebookId);
    setSelectedDatasetId(null);
    setSelectedOption("notebook");
  };

  const handleDatasetDelete = (id) => {
    if (id === selectedDatasetId) {
      setSelectedDatasetId(null);
      setStep(0);
      setSelectedOption(null);
    }

    // Remove the dataset from the state
    setDatasets((prevDatasets) =>
      prevDatasets.filter((dataset) => dataset.id !== id),
    );

    // Remove all notebooks associated with this dataset
    setNotebooks((prevNotebooks) => {
      const filteredNotebooks = prevNotebooks.filter(
        (notebook) => notebook.dataset_id !== id,
      );

      // If the currently selected notebook is being removed, clear the selection
      if (
        selectedNotebookId &&
        prevNotebooks.find(
          (notebook) =>
            notebook.id === selectedNotebookId && notebook.dataset_id === id,
        )
      ) {
        setSelectedNotebookId(null);
        setStep(0);
        setSelectedOption(null);
      }

      return filteredNotebooks;
    });

    deleteDataset(id);
  };

  const handleNotebookDelete = (id) => {
    if (id === selectedNotebookId) {
      setSelectedNotebookId(null);
      setStep(0);
      setSelectedOption(null);
    }

    setNotebooks((prevNotebooks) =>
      prevNotebooks.filter((notebook) => notebook.id !== id),
    );

    deleteNotebook(id);
  };

  const handleAddDatasetFromNotebook = async (name) => {
    if (selectedNotebook) {
      try {
        const data = await createDataset(name);
        enqueueSnackbar("Dataset creation started", {
          variant: "success",
        });
        setDatasets((prev) => [...prev, data]);
        setSelectedDatasetId(data.id);
        setSelectedOption("dataset");
        setSelectedNotebookId(null);

        const job = await enqueueDatasetJob(
          data.id,
          null,
          "",
          {},
          selectedNotebook.id,
        );
        pollForDataset(
          { datasetId: data.id, datasetName: name },
          { jobId: job.id },
        );
      } catch (error) {
        enqueueSnackbar("Failed to create dataset from notebook:", {
          variant: "error",
        });
        console.error("Failed to create dataset from notebook:", error);
      }
    }
  };

  const handleNotebookCreated = async (createdNotebook) => {
    await fetchNotebooks();
    setStep(0);
    setSelectedOption("notebook");
    setSelectedNotebookId(createdNotebook.id);
    setSelectedDatasetId(null);
  };

  const handleDatasetCreated = async (newDataset, datasetJob) => {
    setDatasets((prevDatasets) => [...prevDatasets, newDataset]);
    setSelectedDatasetId(newDataset.id);

    setStep(0);
    setSelectedOption("dataset");
    setSelectedNotebookId(null);

    pollForDataset(
      { datasetId: newDataset.id, datasetName: newDataset.name },
      { jobId: datasetJob.id },
    );
  };

  const pollForDataset = async (
    { datasetId, datasetName },
    { jobId },
    attempt = 1,
    maxAttempts = 10,
  ) => {
    if (jobId && attempt === 1) {
      startJobPolling(
        jobId,
        async (result) => {
          enqueueSnackbar(`Dataset "${datasetName}" created successfully`, {
            variant: "success",
          });

          try {
            const freshDatasets = await getDatasets();
            const dataset = freshDatasets.find((d) => d.id === datasetId);

            if (dataset) {
              const enrichedDatasets = await enrichDatasetsWithInfo(
                freshDatasets,
                datasets,
              );
              setDatasets(enrichedDatasets);
              setSelectedDatasetId(datasetId);
            } else {
              await fetchDatasets();
              setSelectedDatasetId(datasetId);
            }
          } catch (error) {
            console.error("Error fetching datasets:", error);
            await fetchDatasets();
            setSelectedDatasetId(datasetId);
          }
        },
        (result) => {
          console.error(`Dataset job failed:`, result);
          enqueueSnackbar(
            `Error creating dataset: ${result.error || "Unknown error"}`,
            { variant: "error" },
          );
          fetchDatasets();
        },
      );
    }
  };

  const handleEditDataset = async (id, newName) => {
    try {
      const updatedDataset = await updateDataset(id, { name: newName });
      setDatasets((prevDatasets) =>
        prevDatasets.map((dataset) =>
          dataset.id === id
            ? { ...dataset, name: updatedDataset.name }
            : dataset,
        ),
      );
      enqueueSnackbar("Dataset updated successfully", {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update dataset:", error);
      if (error.response?.status === 409) {
        enqueueSnackbar("A dataset with this name already exists", {
          variant: "error",
        });
      } else if (error.response?.status === 422) {
        enqueueSnackbar("Dataset name cannot be empty", {
          variant: "error",
        });
      } else {
        enqueueSnackbar("Failed to update dataset", {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const handleEditNotebook = async (id, newName) => {
    try {
      const updatedNotebook = await updateNotebook(id, { name: newName });
      setNotebooks((prevNotebooks) =>
        prevNotebooks.map((notebook) =>
          notebook.id === id
            ? { ...notebook, name: updatedNotebook.name }
            : notebook,
        ),
      );
      enqueueSnackbar("Notebook updated successfully", {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update notebook:", error);
      if (error.response?.status === 422) {
        enqueueSnackbar("Notebook name cannot be empty", {
          variant: "error",
        });
      } else if (error.response?.status === 304) {
        enqueueSnackbar("No changes were made", {
          variant: "info",
        });
      } else {
        enqueueSnackbar("Failed to update notebook", {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  return (
    <>
      <Box
        height="calc(100vh - 74px)"
        width="100%"
        // p={1.5}
        // pb={1}
        display="flex"
      >
        <Box width="22%" className="datasets-list">
          <LeftBar
            datasets={datasets}
            notebooks={notebooks}
            selectedDatasetId={selectedDatasetId}
            selectedNotebookId={selectedNotebookId}
            onDatasetClick={handleDatasetClick}
            onDatasetDelete={handleDatasetDelete}
            onDatasetEdit={handleEditDataset}
            onNotebookClick={handleNotebookClick}
            onNotebookDelete={handleNotebookDelete}
            onNotebookEdit={handleEditNotebook}
            handleNewSessionButton={handleNewSessionButton}
          />
        </Box>
        <ExplorersAndConvertersProvider>
          {selectedDatasetId ? (
            <>
              <Box width="56%">
                <CenterBox>
                  <DatasetVisualization
                    dataset={selectedDataset}
                    onNotebookCreated={handleNotebookCreated}
                    existingNotebooks={notebooks}
                  />
                </CenterBox>
              </Box>
              <Box width="22%">
                <RightBar notebook={null} />
              </Box>
            </>
          ) : selectedNotebookId ? (
            <TourProvider tourKey={TOUR_KEYS.NOTEBOOK}>
              <Box width="56%">
                <CenterBox>
                  <NotebookVisualization
                    notebook={selectedNotebook}
                    handleAddDatasetFromNotebook={handleAddDatasetFromNotebook}
                    existingDatasets={datasets}
                  />
                </CenterBox>
              </Box>
              <Box width="22%">
                <RightBar notebook={selectedNotebook} />
              </Box>
              <TourButton tourKey={TOUR_KEYS.NOTEBOOK} />
            </TourProvider>
          ) : (
            <>
              <Box width="56%">
                <CenterBox>
                  {step === 0 ? (
                    <SelectOptionMenu
                      title="Dataset Module"
                      subtitle="Upload your datasets: Explore, analyze, and transform your
                   data with advanced exploratory analysis tools. Create interactive notebooks,
                   generate visualizations, and apply data transformations intuitively."
                      options={menuOptions}
                      searchBar={false}
                      goToNextStep={goToNextStep}
                    />
                  ) : step === 1 && selectedOption === "dataset" ? (
                    <UploadDatasetSteps
                      backHome={() => {
                        setStep(0);
                        setSelectedOption(null);
                        fetchDatasets();
                      }}
                      handleDatasetCreated={handleDatasetCreated}
                      existingDatasets={datasets}
                    />
                  ) : step === 1 && selectedOption === "notebook" ? (
                    <UploadNotebookSteps
                      backHome={() => {
                        setStep(0);
                        setSelectedOption(null);
                        fetchNotebooks();
                      }}
                      datasets={datasets}
                      handleNotebookCreated={handleNotebookCreated}
                      existingNotebooks={notebooks}
                    />
                  ) : null}
                </CenterBox>
              </Box>
              <Box width="22%">
                <RightBar notebook={null} />
              </Box>
            </>
          )}
        </ExplorersAndConvertersProvider>
      </Box>
      {!selectedNotebookId && <TourButton tourKey={TOUR_KEYS.DATASETS} />}
    </>
  );
}
