import { useState, useEffect } from "react";
import { Box } from "@mui/material";
import LeftBar from "../../components/notebooks/LeftBar";
import CenterBox from "../../components/notebooks/CenterBox";
import RightBar from "../../components/notebooks/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import UploadDatasetSteps from "../../components/notebooks/UploadDatasetSteps";
import UploadNotebookSteps from "../../components/notebooks/UploadNotebookSteps";
import DatasetView from "../../components/notebooks/DatasetView";
import NotebookVisualization from "../../components/notebooks/NotebookVisualization";
import { getDatasets, deleteDataset } from "../../api/datasets";
import { getNotebooks, deleteNotebook } from "../../api/notebook";

export default function Notebooks() {
  const [step, setStep] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [selectedNotebookId, setSelectedNotebookId] = useState(1);
  const [datasets, setDatasets] = useState([]);
  const [notebooks, setNotebooks] = useState([]);

  const goToNextStep = (option = selectedOption) => {
    setStep((prevStep) => prevStep + 1);
    setSelectedOption(option);
    setSelectedNotebookId(null);
    setSelectedDatasetId(null);
  };

  const fetchDatasets = async () => {
    const data = await getDatasets();
    setDatasets(data);
  };

  const fetchNotebooks = async () => {
    const data = await getNotebooks();
    setNotebooks(data);
  };

  useEffect(() => {
    fetchDatasets();
    fetchNotebooks();
  }, []);

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

    setDatasets((prevDatasets) =>
      prevDatasets.filter((dataset) => dataset.id !== id),
    );

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
          onNotebookClick={handleNotebookClick}
          onNotebookDelete={handleNotebookDelete}
        />
      </Box>
      <Box width="56%" mr={1}>
        <CenterBox>
          {selectedDatasetId ? (
            <DatasetView dataset={selectedDataset} />
          ) : selectedNotebookId ? (
            <NotebookVisualization notebook={selectedNotebook} />
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
            />
          ) : step === 1 && selectedOption === "notebook" ? (
            <UploadNotebookSteps
              backHome={() => {
                setStep(0);
                setSelectedOption(null);
                fetchNotebooks();
              }}
              datasets={datasets}
            />
          ) : null}
        </CenterBox>
      </Box>
      <Box width="22%">
        <RightBar></RightBar>
      </Box>
    </Box>
  );
}
