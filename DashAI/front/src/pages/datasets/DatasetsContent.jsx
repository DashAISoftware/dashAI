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
import { startJobPolling } from "../../utils/jobPoller";
import { enqueueDatasetJob } from "../../api/job";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { useTranslation } from "react-i18next";
import { useDatasets } from "../../hooks/useDatasets";
import { useNotebooks } from "../../hooks/useNotebooks";
import { useDatasetUIState } from "../../hooks/useDatasetUIState";

export default function DatasetsContent() {
  const [leftBarVisible, setLeftBarVisible] = useState(true);
  const [rightBarVisible, setRightBarVisible] = useState(true);
  const [leftBarWidth, setLeftBarWidth] = useState(20);
  const [rightBarWidth, setRightBarWidth] = useState(20);
  const [rightBarContent, setRightBarContent] = useState(null);
  const isResizingLeft = useRef(false);
  const isResizingRight = useRef(false);
  const [isTogglingLeft, setIsTogglingLeft] = useState(false);
  const [isTogglingRight, setIsTogglingRight] = useState(false);
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);

  const {
    datasets,
    selectedDatasetId,
    createDataset,
    fetchDatasets,
    fetchFreshDatasets,
    selectDataset,
    clearSelectedDataset,
    deleteDatasetLocal,
    deleteDatasetRemote,
    editDataset,
    addDatasetOptimistically,
    startDatasetPolling,
    removeDatasetById,
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

  const handleDatasetClick = (datasetId) => {
    selectDataset(datasetId);
    clearSelectedNotebook();
    selectDatasetView();
    setRightBarContent(null);
  };

  const handleNotebookClick = (notebookId) => {
    selectNotebook(notebookId);
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

  const handleAddDatasetFromNotebook = async (name) => {
    if (!selectedNotebook) return;

    try {
      const data = await createDataset(name);

      enqueueSnackbar(t("datasets:message.datasetCreationStarted"), {
        variant: "success",
      });
      addDatasetOptimistically(data);
      selectDatasetView();
      clearSelectedNotebook();

      const job = await enqueueDatasetJob(
        data.id,
        null,
        "",
        {},
        selectedNotebook.id,
      );

      pollForDataset(
        { datasetId: data.id, datasetName: name },
        { jobId: job.id },
      );
    } catch (error) {
      enqueueSnackbar(t("datasets:error.failedToCreateDatasetFromNotebook"), {
        variant: "error",
      });
      console.error("Failed to create dataset from notebook:", error);
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

  const handleDatasetCreated = (newDataset, datasetJob) => {
    addDatasetOptimistically(newDataset);
    selectDatasetView();
    clearSelectedNotebook();
    // clear right bar content injected during dataset creation (e.g. dataloader config)
    setRightBarContent(null);
    startDatasetPolling(newDataset, datasetJob);
  };

  const pollForDataset = async ({ datasetId, datasetName }, { jobId }) => {
    if (!jobId) return;

    startJobPolling(
      jobId,
      async () => {
        enqueueSnackbar(
          t("datasets:message.datasetCreationSuccess", { datasetName }),
          { variant: "success" },
        );

        try {
          const freshDatasets = await fetchFreshDatasets();
          const dataset = freshDatasets.find((d) => d.id === datasetId);

          if (dataset) {
            const enriched = await enrichDatasetsWithInfo(
              freshDatasets,
              datasets,
            );

            replaceDatasets(enriched);
            selectDataset(datasetId);
          } else {
            await fetchDatasets();
            selectDataset(datasetId);
          }
        } catch (error) {
          console.error("Error fetching datasets after job completion:", error);
          await fetchDatasets();
          selectDataset(datasetId);
        }
      },

      async (result) => {
        console.error("Dataset job failed:", result);

        enqueueSnackbar(
          t("datasets:error.failedToCreateDataset", {
            error: result?.error || t("common:unknownError"),
          }),
          { variant: "error" },
        );

        removeDatasetById(datasetId);
        clearSelectedDataset();
        resetUI();
      },
    );
  };

  const handleEditDataset = (id, newName) => editDataset(id, newName);

  const handleEditNotebook = (id, newName) => editNotebook(id, newName);

  const handleMouseMove = useCallback((e) => {
    if (isResizingLeft.current) {
      const container = document.querySelector('[data-container="datasets"]');
      const containerRect = container.getBoundingClientRect();
      const newWidth =
        ((e.clientX - containerRect.left) / containerRect.width) * 100;
      if (newWidth >= 15 && newWidth <= 40) {
        setLeftBarWidth(newWidth);
      }
    }

    if (isResizingRight.current) {
      const container = document.querySelector('[data-container="datasets"]');
      const containerRect = container.getBoundingClientRect();
      const newWidth =
        ((containerRect.right - e.clientX) / containerRect.width) * 100;
      if (newWidth >= 15 && newWidth <= 40) {
        setRightBarWidth(newWidth);
      }
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    isResizingLeft.current = false;
    isResizingRight.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, []);

  const handleToggleLeft = () => {
    setIsTogglingLeft(true);
    setLeftBarVisible(!leftBarVisible);
    setTimeout(() => setIsTogglingLeft(false), 300);
  };

  const handleToggleRight = () => {
    setIsTogglingRight(true);
    setRightBarVisible(!rightBarVisible);
    setTimeout(() => setIsTogglingRight(false), 300);
  };

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const centerWidth =
    leftBarVisible && rightBarVisible
      ? 100 - leftBarWidth - rightBarWidth
      : leftBarVisible
        ? 100 - leftBarWidth
        : rightBarVisible
          ? 100 - rightBarWidth
          : 100;

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
                onMouseDown={() => {
                  isResizingLeft.current = true;
                  document.body.style.cursor = "col-resize";
                  document.body.style.userSelect = "none";
                }}
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
                      handleAddDatasetFromNotebook={
                        handleAddDatasetFromNotebook
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
                        onMouseDown={() => {
                          isResizingRight.current = true;
                          document.body.style.cursor = "col-resize";
                          document.body.style.userSelect = "none";
                        }}
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
                      onMouseDown={() => {
                        isResizingRight.current = true;
                        document.body.style.cursor = "col-resize";
                        document.body.style.userSelect = "none";
                      }}
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
