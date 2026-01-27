import { useState, useEffect, useRef, useCallback } from "react";
import { Box, IconButton } from "@mui/material";
import { ChevronLeft, ChevronRight } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useTourContext } from "../../components/tour/TourProvider";
import LeftBar from "../../components/notebooks/LeftBar";
import CenterBox from "../../components/threeSectionLayout/CenterBox";
import RightBar from "../../components/notebooks/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import UploadDatasetSteps from "../../components/notebooks/datasetCreation/UploadDatasetSteps";
import UploadNotebookSteps from "../../components/notebooks/notebookCreation/UploadNotebookSteps";
import DatasetVisualization from "../../components/DatasetVisualization";
import NotebookVisualization from "../../components/notebooks/notebook/NotebookVisualization";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { useTranslation } from "react-i18next";
import { useDatasets } from "../../hooks/useDatasets";
import { useNotebooks } from "../../hooks/useNotebooks";
import { useDatasetUIState } from "../../hooks/useDatasetUIState";
import { useDatasetFlow } from "../../hooks/useDatasetFlow";
import { useDatasetActions } from "../../hooks/useDatasetActions";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { useNotebookActions } from "../../hooks/useNotebooksActions";

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

  const {
    leftBarVisible,
    rightBarVisible,
    leftBarWidth,
    rightBarWidth,
    centerWidth,

    handleToggleLeft,
    handleToggleRight,

    isTogglingLeft,
    isTogglingRight,

    bindLeftResize,
    bindRightResize,
  } = useThreePanelLayout();

  const {
    handleAddDatasetFromNotebook,
    handleNotebookCreated,
    handleNewNotebookFromDataset,
  } = useNotebookActions({
    fetchNotebooks,
    selectNotebook,
    clearSelectedNotebook,
    clearSelectedDataset,
    selectNotebookView,
    selectDatasetView,
    goToNotebookCreation,
    createDatasetFromNotebook,
  });

  const goToNextStep = (option) => {
    if (option === "dataset") {
      goToDatasetFlow();
    } else {
      goToNotebookFlow();
    }

    clearSelectedNotebook();
    clearSelectedDataset();

    if (option === "dataset" && tourContext?.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 600);
    }
  };

  useEffect(() => {
    fetchDatasets();
    fetchNotebooks();
  }, []);

  const handleNewSessionButton = () => {
    clearSelectedDataset();
    clearSelectedNotebook();
    resetUI();
  };

  const handleDatasetCreated = (newDataset, datasetJob) => {
    addDatasetOptimistically(newDataset);
    selectDatasetView();
    clearSelectedNotebook();
    // clear right bar content injected during dataset creation (e.g. dataloader config)
    setRightBarContent(null);
    startDatasetPolling(newDataset, datasetJob);
  };

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  return (
    <>
      <Box
        height="calc(100vh - 74px)"
        width="100%"
        display="flex"
        data-container="datasets"
      >
        {/* Left Panel */}
        <Box
          width={leftBarVisible ? `${leftBarWidth}%` : "0%"}
          position="relative"
          className="datasets-list"
          sx={{
            transition: isTogglingLeft
              ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease"
              : "none",
            opacity: leftBarVisible ? 1 : 0,
            overflow: "hidden",
          }}
        >
          {leftBarVisible && (
            <>
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
                onToggle={handleToggleLeft}
              />
              <Box
                {...bindLeftResize}
                sx={{
                  position: "absolute",
                  right: -2,
                  top: 0,
                  bottom: 0,
                  width: "5px",
                  cursor: "col-resize",
                  bgcolor: "transparent",
                  transition: "background-color 0.2s ease",
                  "&:hover": {
                    bgcolor: "primary.main",
                  },
                  zIndex: 10,
                }}
              />
            </>
          )}
        </Box>

        {!leftBarVisible && (
          <IconButton
            onClick={handleToggleLeft}
            sx={{
              position: "absolute",
              left: 8,
              top: "50%",
              transform: "translateY(-50%)",
              bgcolor: "background.paper",
              zIndex: 10,
              transition: "all 0.2s ease",
              "&:hover": {
                bgcolor: "action.hover",
                transform: "translateY(-50%) scale(1.1)",
              },
            }}
          >
            <ChevronRight />
          </IconButton>
        )}

        <ExplorersAndConvertersProvider>
          {selectedNotebookId ? (
            <TourProvider tourKey={TOUR_KEYS.NOTEBOOK}>
              <>
                {/* Center Panel - Notebook */}
                <Box
                  width={`${centerWidth}%`}
                  sx={{
                    transition:
                      isTogglingLeft || isTogglingRight
                        ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
                        : "none",
                  }}
                >
                  <CenterBox>
                    <NotebookVisualization
                      notebook={selectedNotebook}
                      handleAddDatasetFromNotebook={(name) =>
                        handleAddDatasetFromNotebook(name, selectedNotebook)
                      }
                      existingDatasets={datasets}
                    />
                  </CenterBox>
                </Box>

                {!rightBarVisible && (
                  <IconButton
                    onClick={handleToggleRight}
                    sx={{
                      position: "absolute",
                      right: 8,
                      top: "calc(50% + 60px)",
                      transform: "translateY(-50%)",
                      bgcolor: "background.paper",
                      zIndex: 10,
                      transition: "all 0.2s ease",
                      "&:hover": {
                        bgcolor: "action.hover",
                        transform: "translateY(-50%) scale(1.1)",
                      },
                    }}
                  >
                    <ChevronLeft />
                  </IconButton>
                )}

                {/* Right Panel - Notebook */}
                <Box
                  width={rightBarVisible ? `${rightBarWidth}%` : "0%"}
                  position="relative"
                  sx={{
                    transition: isTogglingRight
                      ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease"
                      : "none",
                    opacity: rightBarVisible ? 1 : 0,
                    overflow: "hidden",
                  }}
                >
                  {rightBarVisible && (
                    <>
                      <Box
                        {...bindRightResize}
                        sx={{
                          position: "absolute",
                          left: -2,
                          top: 0,
                          bottom: 0,
                          width: "5px",
                          cursor: "col-resize",
                          bgcolor: "transparent",
                          transition: "background-color 0.2s ease",
                          "&:hover": {
                            bgcolor: "primary.main",
                          },
                          zIndex: 10,
                        }}
                      />
                      <RightBar
                        notebook={selectedNotebook}
                        onToggle={handleToggleRight}
                      />
                    </>
                  )}
                </Box>

                <TourButton tourKey={TOUR_KEYS.NOTEBOOK} />
              </>
            </TourProvider>
          ) : (
            <>
              <Box
                width={`${centerWidth}%`}
                sx={{
                  transition:
                    isTogglingLeft || isTogglingRight
                      ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
                      : "none",
                }}
              >
                <CenterBox>
                  {step === 1 && selectedOption === "dataset" ? (
                    <UploadDatasetSteps
                      backHome={() => {
                        resetUI();
                        fetchDatasets();
                        // clear right bar when exiting
                        setRightBarContent(null);
                      }}
                      handleDatasetCreated={handleDatasetCreated}
                      existingDatasets={datasets}
                      renderRightBar={setRightBarContent}
                    />
                  ) : step === 1 && selectedOption === "notebook" ? (
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
                  ) : selectedDatasetId ? (
                    <DatasetVisualization
                      dataset={selectedDataset}
                      onItemCreated={handleNotebookCreated}
                      onNewItem={handleNewNotebookFromDataset}
                      existingItems={notebooks}
                      newItemButtonText={t("datasets:button.newNotebook")}
                    />
                  ) : step === 0 ? (
                    <SelectOptionMenu
                      title={t("datasets:label.datasetModule")}
                      subtitle={t("datasets:label.datasetModuleSubtitle")}
                      options={[
                        {
                          name: "dataset",
                          display_name: t("datasets:label.uploadDataset"),
                          description: t(
                            "datasets:label.uploadDatasetDescription",
                          ),
                          Icon: null,
                          "data-tour": "dataset-option",
                        },
                        {
                          name: "notebook",
                          display_name: t("datasets:label.createNewNotebook"),
                          description: t(
                            "datasets:label.createNewNotebookDescription",
                          ),
                          Icon: null,
                          "data-tour": "notebook-option",
                        },
                      ]}
                      searchBar={false}
                      goToNextStep={goToNextStep}
                    />
                  ) : null}
                </CenterBox>
              </Box>

              {!rightBarVisible && (
                <IconButton
                  onClick={handleToggleRight}
                  sx={{
                    position: "absolute",
                    right: 8,
                    top: "50%",
                    transform: "translateY(-50%)",
                    bgcolor: "background.paper",
                    zIndex: 10,
                    transition: "all 0.2s ease",
                    "&:hover": {
                      bgcolor: "action.hover",
                      transform: "translateY(-50%) scale(1.1)",
                    },
                  }}
                >
                  <ChevronLeft />
                </IconButton>
              )}

              <Box
                width={rightBarVisible ? `${rightBarWidth}%` : "0%"}
                position="relative"
                sx={{
                  transition: isTogglingRight
                    ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease"
                    : "none",
                  opacity: rightBarVisible ? 1 : 0,
                  overflow: "hidden",
                }}
              >
                {rightBarVisible && (
                  <>
                    <Box
                      {...bindLeftResize}
                      sx={{
                        position: "absolute",
                        left: -2,
                        top: 0,
                        bottom: 0,
                        width: "5px",
                        cursor: "col-resize",
                        bgcolor: "transparent",
                        transition: "background-color 0.2s ease",
                        "&:hover": {
                          bgcolor: "primary.main",
                        },
                        zIndex: 10,
                      }}
                    />
                    {rightBarContent ? (
                      rightBarContent
                    ) : (
                      <RightBar notebook={null} onToggle={handleToggleRight} />
                    )}
                  </>
                )}
              </Box>
            </>
          )}
        </ExplorersAndConvertersProvider>
      </Box>
      {!selectedNotebookId && <TourButton tourKey={TOUR_KEYS.DATASETS} />}
    </>
  );
}
