import { useCallback } from "react";
import NotebookVisualization from "../notebook/NotebookVisualization";
import UploadDatasetSteps from "../datasetCreation/UploadDatasetSteps";
import UploadNotebookSteps from "../notebookCreation/UploadNotebookSteps";
import DatasetVisualization from "../../DatasetVisualization";
import SelectOptionMenu from "../../threeSectionLayout/SelectOptionMenu";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";
import { useTourContext } from "../../tour/TourProvider";

export default function DatasetsCenterContent({
  t,
  handleNotebookCreated,
  handleNewNotebookFromDataset,
  handleAddDatasetFromNotebook,
}) {
  const {
    datasets,
    notebooks,
    selectedDatasetId,
    selectedNotebookId,
    step,
    fetchDatasets,
    fetchNotebooks,
    selectedOption,
    setStep,
    setSelectedOption,
    clearSelectedDataset,
    clearSelectedNotebook,
  } = useDatasetsAndNotebooks();

  const tourContext = useTourContext();

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  const resetUI = useCallback(() => {
    setStep(0);
    setSelectedOption(null);
  }, []);

  const goToDatasetFlow = useCallback(() => {
    setStep(1);
    setSelectedOption("dataset");
  }, []);

  const goToNotebookFlow = useCallback(() => {
    setStep(1);
    setSelectedOption("notebook");
  }, []);

  const goToNextStep = (option) => {
    if (option === "dataset") {
      goToDatasetFlow();
    } else {
      goToNotebookFlow();
    }

    clearSelectedDataset();
    clearSelectedNotebook();

    if (option === "dataset" && tourContext?.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 600);
    }
  };

  if (selectedNotebookId) {
    return (
      <NotebookVisualization
        notebook={selectedNotebook}
        handleAddDatasetFromNotebook={handleAddDatasetFromNotebook}
        existingDatasets={datasets}
      />
    );
  }
  if (step === 1 && selectedOption === "dataset") {
    return (
      <UploadDatasetSteps
        backHome={() => {
          resetUI();
          fetchDatasets();
          setRightBarContent(null);
        }}
      />
    );
  }
  if (step === 1 && selectedOption === "notebook") {
    return (
      <UploadNotebookSteps
        backHome={() => {
          resetUI();
          fetchNotebooks();
        }}
        datasets={datasets}
        handleNotebookCreated={handleNotebookCreated}
        existingNotebooks={notebooks}
        preselectedDatasetId={selectedDatasetId}
      />
    );
  }
  if (selectedDatasetId) {
    return (
      <DatasetVisualization
        dataset={selectedDataset}
        onItemCreated={handleNotebookCreated}
        onNewItem={handleNewNotebookFromDataset}
        existingItems={notebooks}
        newItemButtonText={t("datasets:button.newNotebook")}
        tourContextType="datasets"
      />
    );
  }
  if (step === 0) {
    return (
      <SelectOptionMenu
        title={t("datasets:label.datasetModule")}
        subtitle={t("datasets:label.datasetModuleSubtitle")}
        options={[
          {
            name: "dataset",
            display_name: t("datasets:label.uploadDataset"),
            description: t("datasets:label.uploadDatasetDescription"),
            Icon: null,
            "data-tour": "dataset-option",
          },
          {
            name: "notebook",
            display_name: t("datasets:label.createNewNotebook"),
            description: t("datasets:label.createNewNotebookDescription"),
            Icon: null,
            "data-tour": "notebook-option",
          },
        ]}
        searchBar={false}
        goToNextStep={goToNextStep}
      />
    );
  }
  return null;
}
