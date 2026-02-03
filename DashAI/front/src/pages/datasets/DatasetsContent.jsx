import { useState } from "react";
import { useTourContext } from "../../components/tour/TourProvider";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import DatasetsNotebooksLeftBar from "../../components/notebooks/DatasetNotebookLeftBar";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightBar from "../../components/notebooks/RightBar";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import DatasetsCenterContent from "../../components/notebooks/dataset/DatasetsCenterContent";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { useTranslation } from "react-i18next";
import { useDatasets } from "../../hooks/datasets/useDatasets";
import { useNotebooks } from "../../hooks/datasets/useNotebooks";
import { useDatasetUIState } from "../../hooks/datasets/useDatasetUIState";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useDatasetFlow } from "../../hooks/datasets/useDatasetFlow";
import { useDatasetsAndNotebooks } from "../../components/custom/contexts/DatasetsAndNotebooksContext";

export default function DatasetsContent() {
  const [rightBarContent, setRightBarContent] = useState(null);
  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets", "common"]);
  const threePanelLayout = useThreePanelLayout();

  const {
    datasets,
    selectedDatasetId,
    fetchDatasets,
    selectDataset,
    clearSelectedDataset,
    deleteDatasetLocal,
    deleteDatasetRemote,
    editDataset,
    addDatasetOptimistically,
    enrichDatasetsWithInfo,
    replaceDatasets,
    startDatasetPolling,
    notebooks,
    selectedNotebookId,
    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    deleteNotebookById,
    editNotebook,
    removeNotebooksByDatasetId,
  } = useDatasetsAndNotebooks();

  const {
    step,
    selectedOption,
    resetUI,
    goToDatasetFlow,
    goToNotebookFlow,
    goToNotebookCreation,
    selectDatasetView,
    selectNotebookView,
  } = useDatasetUIState();

  const { createDatasetFromNotebook } = useDatasetFlow({
    datasets,
    enrichDatasetsWithInfo,
    fetchDatasets,
    replaceDatasets,
    addDatasetOptimistically,
    selectDataset,
    clearSelectedDataset,
    t,
    resetUI,
    deleteDatasetRemote,
  });

  const handleDatasetClick = (id) => {
    selectDataset(id);
    clearSelectedNotebook();
    selectDatasetView();
  };

  const handleNotebookClick = (id) => {
    selectNotebook(id);
    clearSelectedDataset();
    selectNotebookView();
  };

  const handleDatasetDelete = async (id) => {
    if (id === selectedDatasetId) {
      clearSelectedDataset();
      resetUI();
    }

    deleteDatasetLocal(id);
    removeNotebooksByDatasetId(id);
    await deleteDatasetRemote(id);
  };

  const handleNotebookDelete = (id) => {
    deleteNotebookById(id);

    if (id === selectedNotebookId) {
      clearSelectedNotebook();
      resetUI();
    }
  };

  const handleNotebookCreated = async (createdNotebook) => {
    await fetchNotebooks();
    selectNotebookView();
    selectNotebook(createdNotebook.id);
    clearSelectedDataset();
  };

  const handleNewNotebookFromDataset = () => {
    goToNotebookCreation();
  };

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

  const handleNewSessionButton = () => {
    clearSelectedDataset();
    clearSelectedNotebook();
    resetUI();
  };

  const handleDatasetCreated = (newDataset, datasetJob) => {
    addDatasetOptimistically(newDataset);
    selectDatasetView();
    clearSelectedNotebook();
    setRightBarContent(null);
    startDatasetPolling(newDataset, datasetJob);
  };

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <DatasetsNotebooksLeftBar
            onDatasetClick={handleDatasetClick}
            onDatasetDelete={handleDatasetDelete}
            onDatasetEdit={editDataset}
            onNotebookClick={handleNotebookClick}
            onNotebookDelete={handleNotebookDelete}
            onNotebookEdit={editNotebook}
            handleNewSessionButton={handleNewSessionButton}
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>

        <ExplorersAndConvertersProvider>
          {selectedNotebookId ? (
            <TourProvider tourKey={TOUR_KEYS.NOTEBOOK}>
              <>
                <CenterPanel>
                  <DatasetsCenterContent
                    selectedNotebookId={selectedNotebookId}
                    selectedNotebook={selectedNotebook}
                    step={step}
                    selectedOption={selectedOption}
                    selectedDatasetId={selectedDatasetId}
                    selectedDataset={selectedDataset}
                    datasets={datasets}
                    notebooks={notebooks}
                    t={t}
                    goToNextStep={goToNextStep}
                    resetUI={resetUI}
                    fetchDatasets={fetchDatasets}
                    fetchNotebooks={fetchNotebooks}
                    setRightBarContent={setRightBarContent}
                    handleDatasetCreated={handleDatasetCreated}
                    handleNotebookCreated={handleNotebookCreated}
                    handleNewNotebookFromDataset={handleNewNotebookFromDataset}
                    handleAddDatasetFromNotebook={createDatasetFromNotebook}
                  />
                </CenterPanel>
                <RightPanel toggleButtonTop="calc(50% + 60px)">
                  {rightBarContent ? (
                    rightBarContent
                  ) : (
                    <RightBar
                      notebook={selectedNotebook}
                      onToggle={threePanelLayout.handleToggleRight}
                    />
                  )}
                </RightPanel>
                <TourButton tourKey={TOUR_KEYS.NOTEBOOK} />
              </>
            </TourProvider>
          ) : (
            <>
              <CenterPanel>
                <DatasetsCenterContent
                  selectedNotebookId={selectedNotebookId}
                  selectedNotebook={selectedNotebook}
                  step={step}
                  selectedOption={selectedOption}
                  selectedDatasetId={selectedDatasetId}
                  selectedDataset={selectedDataset}
                  datasets={datasets}
                  notebooks={notebooks}
                  t={t}
                  goToNextStep={goToNextStep}
                  resetUI={resetUI}
                  fetchDatasets={fetchDatasets}
                  fetchNotebooks={fetchNotebooks}
                  setRightBarContent={setRightBarContent}
                  handleDatasetCreated={handleDatasetCreated}
                  handleNotebookCreated={handleNotebookCreated}
                  handleNewNotebookFromDataset={handleNewNotebookFromDataset}
                  handleAddDatasetFromNotebook={createDatasetFromNotebook}
                />
              </CenterPanel>
              <RightPanel toggleButtonTop="50%">
                {rightBarContent ? (
                  rightBarContent
                ) : (
                  <RightBar
                    notebook={null}
                    onToggle={threePanelLayout.handleToggleRight}
                  />
                )}
              </RightPanel>
            </>
          )}
        </ExplorersAndConvertersProvider>
      </ModuleContainer>
      {!selectedNotebookId && <TourButton tourKey={TOUR_KEYS.DATASETS} />}
    </ThreePanelLayoutContext.Provider>
  );
}
