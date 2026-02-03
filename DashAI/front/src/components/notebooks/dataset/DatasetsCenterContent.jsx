import NotebookVisualization from "../notebook/NotebookVisualization";
import UploadDatasetSteps from "../datasetCreation/UploadDatasetSteps";
import UploadNotebookSteps from "../notebookCreation/UploadNotebookSteps";
import DatasetVisualization from "../../DatasetVisualization";
import SelectOptionMenu from "../../threeSectionLayout/SelectOptionMenu";

export default function DatasetsCenterContent({
  selectedNotebookId,
  selectedNotebook,
  step,
  selectedOption,
  selectedDatasetId,
  selectedDataset,
  datasets,
  notebooks,
  t,
  goToNextStep,
  resetUI,
  fetchDatasets,
  fetchNotebooks,
  setRightBarContent,
  handleDatasetCreated,
  handleNotebookCreated,
  handleNewNotebookFromDataset,
  handleAddDatasetFromNotebook,
}) {
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
        handleDatasetCreated={handleDatasetCreated}
        existingDatasets={datasets}
        renderRightBar={setRightBarContent}
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
