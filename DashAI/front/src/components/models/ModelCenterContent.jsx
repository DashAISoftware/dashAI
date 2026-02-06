import { useModels } from "./ModelsContext";
import { useTranslation } from "react-i18next";
import CreateSessionSteps from "./CreateSessionSteps";
import DatasetVisualization from "../DatasetVisualization";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";
import { useTourContext } from "../tour/TourProvider";

export default function ModelsCenterContent({
  handleBackToTaskSelection,
  handleGoToDatasets,
  handleSessionCreated,
  handleNewSessionFromDataset,
  handleBackToDataset,
}) {
  const { t } = useTranslation(["models", "datasets", "common"]);
  const tourContext = useTourContext();
  const {
    sessions,
    selectedTask,
    tasks,
    datasets,
    selectedDatasetId,
    step,
    setSelectedTask,
    setStep,
  } = useModels();

  const goToNextStep = (taskName) => {
    const task = tasks.find((t) => t.name === taskName);
    setSelectedTask(task);
    setStep(1);

    if (tourContext?.run && tourContext?.stepIndex === 4) {
      const waitForElement = () => {
        const element = document.querySelector(
          '[data-tour="models-dataset-selection"]',
        );
        if (element) {
          tourContext.nextStep();
        } else {
          setTimeout(waitForElement, 100);
        }
      };
      setTimeout(waitForElement, 100);
    }
  };

  return (
    <>
      {step === 1 && selectedTask ? (
        <CreateSessionSteps
          backHome={handleBackToTaskSelection}
          selectedTask={selectedTask}
          datasets={datasets}
          handleSessionCreated={handleSessionCreated}
          existingSessions={sessions}
          preselectedDatasetId={selectedDatasetId}
        />
      ) : step === 2 && selectedDatasetId ? (
        <DatasetVisualization
          dataset={datasets.find((d) => d.id === selectedDatasetId)}
          onItemCreated={handleSessionCreated}
          onNewItem={handleNewSessionFromDataset}
          existingItems={sessions}
          newItemButtonText={t("models:button.createSession")}
        />
      ) : step === 0 ? (
        <SelectOptionMenu
          title={
            selectedDatasetId
              ? t("models:label.selectTaskForSession")
              : t("models:label.modelsModule")
          }
          subtitle={
            selectedDatasetId
              ? t("models:label.chooseTaskForSessionWithDataset", {
                  datasetName: datasets.find((d) => d.id === selectedDatasetId)
                    ?.name,
                })
              : t("models:label.configureTasksTrainCompareModels")
          }
          options={tasks.map((task) => ({
            name: task.name,
            display_name:
              task.display_name ||
              task.name
                .replace("Task", "")
                .replace(/([A-Z])/g, " $1")
                .trim(),
            description:
              task.description || task.metadata?.short_description || "",
            Icon: null,
          }))}
          searchBar={true}
          goToPrevStep={selectedDatasetId ? handleBackToDataset : null}
          showNoDatasetAlert={!selectedDatasetId && datasets.length === 0}
          onGoToDatasets={handleGoToDatasets}
          goToNextStep={goToNextStep}
        />
      ) : null}
    </>
  );
}
