import { useState, useEffect } from "react";
import { useSnackbar } from "notistack";
import { useTourContext } from "../../components/tour/TourProvider";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import LeftBar from "../../components/notebooks/LeftBar";
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
import { useDatasetFlow } from "../../hooks/datasets/useDatasetFlow";
import { useDatasetActions } from "../../hooks/datasets/useDatasetActions";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useNotebookActions } from "../../hooks/datasets/useNotebooksActions";
import { useLayoutActions } from "../../hooks/datasets/useLayoutActions";

export default function DatasetsContent() {
  const [rightBarContent, setRightBarContent] = useState(null);
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

  const {
    datasets,
    selectedDatasetId,
    enrichDatasetsWithInfo,
    fetchDatasets,
    selectDataset,
    clearSelectedDataset,
    deleteDatasetLocal,
    deleteDatasetRemote,
    editDataset,
    addDatasetOptimistically,
    startDatasetPolling,
    replaceDatasets,
  } = useDatasets({ enqueueSnackbar, t });

  const {
    notebooks,
    selectedNotebookId,
    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    deleteNotebookById,
    editNotebook,
    removeNotebooksByDatasetId,
  } = useNotebooks({ enqueueSnackbar, t });

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
    selectDataset,
    clearSelectedDataset,
    deleteDatasetRemote,
    enqueueSnackbar,
    t,
    resetUI,
  });

  const {
    handleDatasetClick,
    handleNotebookClick,
    handleDatasetDelete,
    handleNotebookDelete,
    handleEditDataset,
    handleEditNotebook,
  } = useDatasetActions({
    selectedDatasetId,
    selectedNotebookId,

    selectDataset,
    selectNotebook,
    clearSelectedDataset,
    clearSelectedNotebook,

    deleteDatasetLocal,
    deleteDatasetRemote,
    removeNotebooksByDatasetId,
    deleteNotebookById,

    editDataset,
    editNotebook,

    resetUI,
    selectDatasetView,
    selectNotebookView,
  });

  const threePanelLayout = useThreePanelLayout();

  const { handleNotebookCreated, handleNewNotebookFromDataset } =
    useNotebookActions({
      fetchNotebooks,
      selectNotebook,
      clearSelectedNotebook,
      clearSelectedDataset,
      selectNotebookView,
      selectDatasetView,
      goToNotebookCreation,
      createDatasetFromNotebook,
    });

  const { goToNextStep, handleNewSessionButton, handleDatasetCreated } =
    useLayoutActions({
      goToDatasetFlow,
      goToNotebookFlow,
      resetUI,

      clearSelectedDataset,
      clearSelectedNotebook,

      selectDatasetView,

      addDatasetOptimistically,
      startDatasetPolling,

      setRightBarContent,
      tourContext,
    });

  useEffect(() => {
    fetchDatasets();
    fetchNotebooks();
  }, []);

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  return (
    <>
      <ThreePanelLayoutContext.Provider value={threePanelLayout}>
        <ModuleContainer>
          <LeftPanel>
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
                      handleNewNotebookFromDataset={
                        handleNewNotebookFromDataset
                      }
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
    </>
  );
}
