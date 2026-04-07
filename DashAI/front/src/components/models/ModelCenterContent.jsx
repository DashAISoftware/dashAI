import { useModels } from "./ModelsContext";
import { useTranslation } from "react-i18next";
import CreateSessionSteps from "./CreateSessionSteps";
import DatasetVisualization from "../DatasetVisualization";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";
import { useTourContext } from "../tour/TourProvider";
import { useNavigate } from "react-router-dom";
import {
  Category as ClassificationIcon,
  ShowChart as RegressionIcon,
  TextFields as TextClassificationIcon,
  TableChart as TabularClassificationIcon,
  Translate as TranslationIcon,
  Science as DefaultTaskIcon,
} from "@mui/icons-material";

const TASK_ICONS = {
  ClassificationTask: ClassificationIcon,
  TabularClassificationTask: TabularClassificationIcon,
  TextClassificationTask: TextClassificationIcon,
  RegressionTask: RegressionIcon,
  TranslationTask: TranslationIcon,
};

export default function ModelsCenterContent() {
  const { t } = useTranslation(["models", "datasets", "common"]);
  const tourContext = useTourContext();
  const navigate = useNavigate();
  const {
    sessions,
    setSessions,
    selectedTask,
    tasks,
    datasets,
    selectedDatasetId,
    step,
    setSelectedTask,
    setSelectedSessionId,
    setStep,
    selectDataset,
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

  const handleBackToTaskSelection = () => {
    setSelectedTask(null);
    setStep(0);
  };

  const handleGoToDatasets = () => {
    navigate("/app/data");
  };

  const handleSessionCreated = (newSession) => {
    setSessions((prev) => [...prev, newSession]);
    setSelectedSessionId(newSession.id);
    selectDataset(null);
  };

  const handleNewSessionFromDataset = () => {
    // Keep the selectedDatasetId but go to task selection
    setSelectedSessionId(null);
    setSelectedTask(null);
    setStep(0);
  };

  const handleBackToDataset = () => {
    // Go back to dataset visualization from task selection
    setSelectedTask(null);
    setStep(2);
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
            Icon: TASK_ICONS[task.name] || DefaultTaskIcon,
          }))}
          searchBar={true}
          goToPrevStep={selectedDatasetId ? handleBackToDataset : null}
          showNoDatasetAlert={!selectedDatasetId && datasets.length === 0}
          onGoToDatasets={handleGoToDatasets}
          goToNextStep={goToNextStep}
          dataTour="task-selection"
        />
      ) : null}
    </>
  );
}
