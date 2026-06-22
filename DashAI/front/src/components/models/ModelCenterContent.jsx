import { useModels } from "./ModelsContext";
import { useTranslation } from "react-i18next";
import { Box } from "@mui/material";
import { useState, useEffect } from "react";
import Joyride from "react-joyride";
import CreateSessionSteps from "./CreateSessionSteps";
import DatasetVisualization from "../DatasetVisualization";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";
import ModelsBreadcrumbs from "./ModelsBreadcrumbs";
import { useTourContext } from "../tour/TourProvider";
import { useNavigate, useLocation } from "react-router-dom";
import { useTheme } from "@mui/material/styles";
import { getTourStyles } from "../tour/tourStyles";
import { CustomTooltip } from "../tour/CustomTooltip";
import {
  energyModelsSteps,
  energyTutorialConfig,
} from "../../constants/tours/tutorials/energyTutorial";
import {
  Category as ClassificationIcon,
  ShowChart as RegressionIcon,
  TextFields as TextClassificationIcon,
  TableChart as TabularClassificationIcon,
  Translate as TranslationIcon,
  ImageSearch as ImageClassificationIcon,
  Science as DefaultTaskIcon,
} from "@mui/icons-material";

const TASK_ICONS = {
  ClassificationTask: ClassificationIcon,
  TabularClassificationTask: TabularClassificationIcon,
  TextClassificationTask: TextClassificationIcon,
  ImageClassificationTask: ImageClassificationIcon,
  RegressionTask: RegressionIcon,
  TranslationTask: TranslationIcon,
};

export default function ModelsCenterContent() {
  const { t } = useTranslation(["models", "datasets", "common"]);
  const tourContext = useTourContext();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const [energyStep3Run, setEnergyStep3Run] = useState(false);
  const [energyStep3Index, setEnergyStep3Index] = useState(0);

  useEffect(() => {
    if (sessionStorage.getItem("energyTutorialContinue") === "true") {
      sessionStorage.removeItem("energyTutorialContinue");
      const waitForRegressionTask = (attempts = 0) => {
        const element = document.querySelector(
          '[data-tour-extra="regression-task"]',
        );
        if (element) {
          setEnergyStep3Run(true);
        } else if (attempts < 30) {
          setTimeout(() => waitForRegressionTask(attempts + 1), 200);
        }
      };
      setTimeout(() => waitForRegressionTask(), 300);
    }
  }, [location.pathname]);
  const {
    sessions,
    setSessions,
    selectedTask,
    tasks,
    loadingTasks,
    datasets,
    selectedDatasetId,
    step,
  } = useModels();

  const goToNextStep = (taskName) => {
    navigate(`/app/models/sessions/new/${taskName}`);

    if (energyStep3Run) {
      const waitForDatasetSelection = (attempts = 0) => {
        const element = document.querySelector(
          '[data-tour="models-dataset-selection"]',
        );
        if (element) {
          setEnergyStep3Index(1);
        } else if (attempts < 30) {
          setTimeout(() => waitForDatasetSelection(attempts + 1), 100);
        }
      };
      setTimeout(waitForDatasetSelection, 100);
    }

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
    navigate("/app/models");
  };

  const handleGoToDatasets = () => {
    navigate("/app/data?action=upload");
  };

  const handleSessionCreated = (newSession) => {
    if (energyStep3Run) {
      sessionStorage.setItem("energyTutorialSessionContinue", "true");
      setEnergyStep3Run(false);
    }
    setSessions((prev) => [...prev, newSession]);
    navigate(`/app/models/sessions/${newSession.id}`);
  };

  const handleNewSessionFromDataset = () => {
    navigate("/app/models", {
      state: { preselectedDatasetId: selectedDatasetId },
    });
  };

  const handleBackToDataset = () => {
    if (selectedDatasetId) {
      navigate(`/app/models/datasets/${selectedDatasetId}`);
      return;
    }
    navigate("/app/models");
  };

  return (
    <>
      <Joyride
        steps={energyModelsSteps}
        run={energyStep3Run}
        stepIndex={energyStep3Index}
        continuous={energyTutorialConfig.continuous}
        showProgress={energyTutorialConfig.showProgress}
        showSkipButton={energyTutorialConfig.showSkipButton}
        showBackButton={energyTutorialConfig.showBackButton}
        disableOverlayClose={energyTutorialConfig.disableOverlayClose}
        disableCloseOnEsc={energyTutorialConfig.disableCloseOnEsc}
        disableOverlay={energyStep3Index === 1}
        styles={getTourStyles(theme)}
        tooltipComponent={CustomTooltip}
        disableScrollParentFix
        floaterProps={{ disableFlip: true, hideArrow: true, offset: 18 }}
        callback={({ status, type, action, index }) => {
          if (status === "skipped" || action === "close") {
            setEnergyStep3Run(false);
          } else if (type === "step:after") {
            if (action === "next" || action === "start") {
              if (index < energyModelsSteps.length - 1) {
                setEnergyStep3Index(index + 1);
              }
            } else if (action === "prev") {
              setEnergyStep3Index(Math.max(index - 1, 0));
            }
          }
        }}
      />
      {step === 1 && selectedTask ? (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            width: "100%",
            height: "100%",
            overflow: "hidden",
            px: 4,
            pt: 4,
          }}
        >
          <ModelsBreadcrumbs />
          <CreateSessionSteps
            backHome={handleBackToTaskSelection}
            selectedTask={selectedTask}
            datasets={datasets}
            handleSessionCreated={handleSessionCreated}
            existingSessions={sessions}
            preselectedDatasetId={selectedDatasetId}
          />
        </Box>
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
          loading={loadingTasks}
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
            ...(task.name === "RegressionTask"
              ? { dataTourExtra: "regression-task" }
              : {}),
          }))}
          searchBar={false}
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
