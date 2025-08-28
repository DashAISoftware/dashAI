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
} from "../../api/datasets";
import {
  getNotebooks,
  deleteNotebook,
  createDatasetFromNotebook,
  updateNotebook,
} from "../../api/notebook";
import { useSnackbar } from "notistack";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";

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
        // Check if we already have enriched info for this dataset
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

  const handleDatasetCreated = async (tempDataset) => {
    // Temporary dataset
    setDatasets((prevDatasets) => [...prevDatasets, tempDataset]);
    setStep(0);
    setSelectedOption("dataset");
    setSelectedDatasetId(tempDataset.id);
    setSelectedNotebookId(null);

    // Real dataset
    const pollForRealDataset = async (attempt = 1, maxAttempts = 10) => {
      try {
        const realDatasets = await getDatasets();
        const realDataset = realDatasets.find(
          (d) =>
            d.name === tempDataset.name && !d.id.toString().startsWith("temp_"),
        );

        if (realDataset) {
          const enrichedDatasets = await enrichDatasetsWithInfo(
            realDatasets,
            datasets,
          );
          setDatasets(enrichedDatasets);
          setSelectedDatasetId(realDataset.id);
        } else if (attempt < maxAttempts) {
          const delay = Math.min(2000 + attempt * 1000, 10000); // Max 10s
          setTimeout(() => pollForRealDataset(attempt + 1, maxAttempts), delay);
        } else {
          console.log(
            "Max polling attempts reached, keeping temporary dataset",
          );
          await fetchDatasets();
        }
      } catch (error) {
        console.error("Error polling for real dataset:", error);
        if (attempt < maxAttempts) {
          setTimeout(() => pollForRealDataset(attempt + 1, maxAttempts), 5000);
        }
      }
    };

    //setTimeout(() => pollForRealDataset(), 1000);
    pollForRealDataset();
  };

  const handleEditDataset = async (id, newName) => {
    try {
      const updatedDataset = await updateDataset(id, { name: newName });
      setDatasets((prevDatasets) =>
        prevDatasets.map((dataset) =>
          dataset.id === id ? { ...dataset, name: newName } : dataset,
        ),
      );
    } catch (error) {
      console.error("Failed to update dataset:", error);
    }
  };

  const handleEditNotebook = async (id, newName) => {
    try {
      const updatedNotebook = await updateNotebook(id, { name: newName });
      setNotebooks((prevNotebooks) =>
        prevNotebooks.map((notebook) =>
          notebook.id === id ? updatedNotebook : notebook,
        ),
      );
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
