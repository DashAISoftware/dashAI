import { useState, useEffect, useRef } from "react";
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
} from "../../api/datasets";
import {
  getNotebooks,
  deleteNotebook,
  createDatasetFromNotebook,
  updateNotebook,
} from "../../api/notebook";
import { useSnackbar } from "notistack";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { getDatasetStatus } from "../../utils/datasetStatus";

export default function DatasetsPage() {
  const [step, setStep] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [selectedNotebookId, setSelectedNotebookId] = useState(0);
  const [datasets, setDatasets] = useState([]);
  const [notebooks, setNotebooks] = useState([]);
  const { enqueueSnackbar } = useSnackbar();

  const goToNextStep = (option = selectedOption) => {
    setStep((prevStep) => prevStep + 1);
    setSelectedOption(option);
    setSelectedNotebookId(null);
    setSelectedDatasetId(null);
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
          // Preserve existing enriched description
          return {
            ...dataset,
            description: existingDataset.description,
          };
        }

        // Fetch new info for this dataset
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
        const data = await createDatasetFromNotebook(selectedNotebook.id, name);

        if (data) {
          enqueueSnackbar("Dataset created successfully", {
            variant: "success",
          });
          const enrichedDatasets = await enrichDatasetsWithInfo(
            [data],
            datasets,
          );
          const enrichedNewDataset = enrichedDatasets[0];

          setDatasets((prevDatasets) => [...prevDatasets, enrichedNewDataset]);
        }
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

  const timerId = useRef(null);

  const handleDatasetCreated = async (newDataset) => {
    setDatasets((prevDatasets) => [...prevDatasets, newDataset]);
    setSelectedDatasetId(newDataset.id);

    setStep(0);
    setSelectedOption("dataset");
    setSelectedNotebookId(null);

    // Check and wait for new dataset to be ready:
    const checkDatasetReady = async () => {
      try {
        const freshDatasets = await getDatasets();

        const dataset = freshDatasets.find((d) => d.id === newDataset.id);
        if (!dataset) {
          console.error("Dataset not found in response:", newDataset.id);
          return;
        }

        if (getDatasetStatus(dataset.status) === "Finished") {
          // Get current datasets and enrich with preserved data
          setDatasets((currentDatasets) => {
            enrichDatasetsWithInfo(freshDatasets, currentDatasets).then(
              setDatasets,
            );
            return currentDatasets;
          });
        } else if (getDatasetStatus(dataset.status) === "Error") {
          console.error("Dataset creation failed:", dataset.error);
          enqueueSnackbar("Dataset creation failed:", {
            variant: "error",
          });
        } else {
          timerId.current = setTimeout(checkDatasetReady, 1000);
        }
      } catch (error) {
        console.error("Error checking dataset readiness:", error);
      }
    };

    checkDatasetReady();
  };

  useEffect(() => {
    return () => {
      if (timerId.current) {
        clearTimeout(timerId.current);
      }
    };
  }, []);

  const handleEditDataset = async (id, newName) => {
    try {
      updateDataset(id, { name: newName }).then(async (updatedDataset) => {
        setDatasets((prevDatasets) =>
          prevDatasets.map((dataset) =>
            dataset.id === id
              ? { ...dataset, name: updatedDataset.name }
              : dataset,
          ),
        );
      });
    } catch (error) {
      console.error("Failed to update dataset:", error);
    }
  };

  const handleEditNotebook = async (id, newName) => {
    try {
      await updateNotebook(id, { name: newName }).then((updatedNotebook) => {
        setNotebooks((prevNotebooks) =>
          prevNotebooks.map((notebook) =>
            notebook.id === id
              ? { ...notebook, name: updatedNotebook.name }
              : notebook,
          ),
        );
      });
    } catch (error) {
      console.error("Failed to update notebook:", error);
    }
  };

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  return (
    <Box height="calc(100vh - 74px)" width="100%" p={1.5} pb={1} display="flex">
      <Box width="22%" mr={1}>
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
        <Box width="56%" mr={1}>
          <CenterBox>
            {selectedDatasetId ? (
              <DatasetVisualization
                dataset={selectedDataset}
                onNotebookCreated={handleNotebookCreated}
                existingNotebooks={notebooks}
              />
            ) : selectedNotebookId ? (
              <NotebookVisualization
                notebook={selectedNotebook}
                handleAddDatasetFromNotebook={handleAddDatasetFromNotebook}
              />
            ) : step === 0 ? (
              <SelectOptionMenu
                title="Dataset Module"
                subtitle="Upload your datasets: Explore, analyze, and transform your
               data with advanced exploratory analysis tools. Create interactive notebooks,
               generate visualizations, and apply data transformations intuitively."
                options={[
                  {
                    name: "dataset",
                    display_name: "Upload Dataset",
                    description:
                      "Import your data from various sources and formats.",
                    Icon: null,
                  },
                  {
                    name: "notebook",
                    display_name: "Create a New Notebook",
                    description:
                      "Start a new analysis session with an existing dataset.",
                    Icon: null,
                  },
                ]}
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
          <RightBar notebook={selectedNotebook} />
        </Box>
      </ExplorersAndConvertersProvider>
    </Box>
  );
}
