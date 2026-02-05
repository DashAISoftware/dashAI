import { useCallback } from "react";
import NotebookVisualization from "../notebook/NotebookVisualization";
import UploadDatasetSteps from "../datasetCreation/UploadDatasetSteps";
import UploadNotebookSteps from "../notebookCreation/UploadNotebookSteps";
import DatasetVisualization from "../../DatasetVisualization";
import SelectOptionMenu from "../../threeSectionLayout/SelectOptionMenu";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

export default function DatasetsCenterContent() {
  const {
    datasets,
    notebooks,
    selectNotebook,
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
  const { t } = useTranslation(["datasets", "common"]);

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  const goToNextStep = useCallback(
    (option) => {
      if (option === "dataset") {
        setStep(1);
        setSelectedOption("dataset");
      } else {
        setStep(1);
        setSelectedOption("notebook");
      }

      clearSelectedDataset();
      clearSelectedNotebook();

      if (option === "dataset" && tourContext?.run) {
        setTimeout(() => {
          tourContext.nextStep();
        }, 600);
      }
    },
    [tourContext],
  );

  const handleNotebookCreated = async (createdNotebook) => {
    await fetchNotebooks();
    setStep(0);
    setSelectedOption("notebook");
    selectNotebook(createdNotebook.id);
    clearSelectedDataset();
  };

  const handleNewNotebookFromDataset = () => {
    setSelectedOption("notebook");
    setStep(1);
  };

  if (selectedNotebookId && selectedOption === "notebook") {
    return (
      <NotebookVisualization
        notebook={selectedNotebook}
        existingDatasets={datasets}
      />
    );
  }

  if (selectedDatasetId && selectedOption === "dataset") {
    return (
      <DatasetVisualization
        dataset={selectedDataset}
        onNewItem={handleNewNotebookFromDataset}
        newItemButtonText={t("datasets:button.newNotebook")}
        tourContextType="datasets"
      />
    );
  }

  if (step === 1 && selectedOption === "dataset") {
    return (
      <UploadDatasetSteps
        backHome={() => {
          setStep(0);
          setSelectedOption(null);
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
          setStep(0);
          setSelectedOption(null);
          fetchNotebooks();
        }}
        datasets={datasets}
        handleNotebookCreated={handleNotebookCreated}
        existingNotebooks={notebooks}
        preselectedDatasetId={selectedDatasetId}
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
