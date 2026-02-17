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
import {
  getDatasets,
  deleteDataset,
  getDatasetInfo,
  updateDataset,
  createDataset,
} from "../../api/datasets";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import { startJobPolling } from "../../utils/jobPoller";
import {
  getNotebooks,
  deleteNotebook,
  updateNotebook,
} from "../../api/notebook";
import { enqueueDatasetJob } from "../../api/job";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { useTranslation } from "react-i18next";

export default function DatasetsContent() {
  const [step, setStep] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [selectedNotebookId, setSelectedNotebookId] = useState(0);
  const [datasets, setDatasets] = useState([]);
  const [notebooks, setNotebooks] = useState([]);
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

  const goToNextStep = (option) => {
    if (option === "dataset" && tourContext?.run) {
      setStep((prevStep) => prevStep + 1);
      setSelectedOption(option);
      setSelectedNotebookId(null);
      setSelectedDatasetId(null);
      setTimeout(() => {
        tourContext.nextStep();
      }, 600);
    } else {
      setStep((prevStep) => prevStep + 1);
      setSelectedOption(option);
      setSelectedNotebookId(null);
      setSelectedDatasetId(null);
    }
  };

  const enrichDatasetsWithInfo = async (newDatasets, existingDatasets = []) => {
    const enrichedDatasets = await Promise.all(
      newDatasets.map(async (dataset) => {
        const existingDataset = existingDatasets.find(
          (d) => d.id === dataset.id,
        );
        if (existingDataset) {
          return {
            ...dataset,
            total_rows: existingDataset.total_rows,
            total_columns: existingDataset.total_columns,
          };
        }

        try {
          const info = await getDatasetInfo(dataset.id);
          return {
            ...dataset,
            total_rows: info.total_rows,
            total_columns: info.total_columns,
          };
        } catch (error) {
          console.warn(
            `Failed to fetch info for dataset ${dataset.id}:`,
            error,
          );
          return {
            ...dataset,
            total_rows: dataset.total_rows,
            columns: dataset.total_columns,
          };
        }
      }),
    );
    return enrichedDatasets;
  };

  const fetchDatasets = async () => {
    try {
      const data = await getDatasets();
      const enrichedDatasets = await enrichDatasetsWithInfo(data, datasets);
      setDatasets(enrichedDatasets);
    } catch (error) {
      enqueueSnackbar(t("datasets:error.failedToFetchDatasets"), {
        variant: "error",
      });
      console.error("Failed to fetch datasets:", error);
    }
  };

  const fetchNotebooks = async () => {
    try {
      const data = await getNotebooks();
      setNotebooks(data);
    } catch (error) {
      enqueueSnackbar(t("datasets:error.failedToFetchNotebooks"), {
        variant: "error",
      });
      console.error("Failed to fetch notebooks:", error);
    }
  };

  useEffect(() => {
    fetchDatasets();
    fetchNotebooks();
  }, []);

  const handleNewSessionButton = () => {
    setSelectedDatasetId(null);
    setSelectedNotebookId(null);
    setStep(0);
    setSelectedOption(null);
  };

  const handleDatasetClick = (datasetId) => {
    setSelectedDatasetId(datasetId);
    setSelectedNotebookId(null);
    setSelectedOption("dataset");
    setRightBarContent(null);
  };

  const handleNotebookClick = (notebookId) => {
    setSelectedNotebookId(notebookId);
    setSelectedDatasetId(null);
    setSelectedOption("notebook");
  };

  const handleDatasetDelete = (id) => {
    if (id === selectedDatasetId) {
      setSelectedDatasetId(null);
      setStep(0);
      setSelectedOption(null);
    }

    setDatasets((prevDatasets) =>
      prevDatasets.filter((dataset) => dataset.id !== id),
    );

    setNotebooks((prevNotebooks) => {
      const filteredNotebooks = prevNotebooks.filter(
        (notebook) => notebook.dataset_id !== id,
      );

      if (
        selectedNotebookId &&
        prevNotebooks.find(
          (notebook) =>
            notebook.id === selectedNotebookId && notebook.dataset_id === id,
        )
      ) {
        setSelectedNotebookId(null);
        setStep(0);
        setSelectedOption(null);
      }

      return filteredNotebooks;
    });

    deleteDataset(id);
  };

  const handleNotebookDelete = (id) => {
    if (id === selectedNotebookId) {
      setSelectedNotebookId(null);
      setStep(0);
      setSelectedOption(null);
    }

    setNotebooks((prevNotebooks) =>
      prevNotebooks.filter((notebook) => notebook.id !== id),
    );

    deleteNotebook(id);
  };

  const handleAddDatasetFromNotebook = async (name) => {
    if (selectedNotebook) {
      try {
        const data = await createDataset(name);
        enqueueSnackbar(t("datasets:message.datasetCreationStarted"), {
          variant: "success",
        });
        setDatasets((prev) => [...prev, data]);
        setSelectedDatasetId(data.id);
        setSelectedOption("dataset");
        setSelectedNotebookId(null);

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
    }
  };

  const handleNotebookCreated = async (createdNotebook) => {
    await fetchNotebooks();
    setStep(0);
    setSelectedOption("notebook");
    setSelectedNotebookId(createdNotebook.id);
    setSelectedDatasetId(null);
  };

  const handleNewNotebookFromDataset = () => {
    // Keep selectedDatasetId but go to notebook creation
    setSelectedOption("notebook");
    setStep(1);
  };

  const handleDatasetCreated = async (newDataset, datasetJob) => {
    setDatasets((prevDatasets) => [...prevDatasets, newDataset]);
    setSelectedDatasetId(newDataset.id);

    setStep(0);
    setSelectedOption("dataset");
    setSelectedNotebookId(null);

    // clear right bar content injected during dataset creation (e.g. dataloader config)
    setRightBarContent(null);

    pollForDataset(
      { datasetId: newDataset.id, datasetName: newDataset.name },
      { jobId: datasetJob.id },
    );
  };

  const pollForDataset = async (
    { datasetId, datasetName },
    { jobId },
    attempt = 1,
    maxAttempts = 10,
  ) => {
    if (jobId && attempt === 1) {
      startJobPolling(
        jobId,
        async (result) => {
          enqueueSnackbar(
            t("datasets:message.datasetCreationSuccess", { datasetName }),
            {
              variant: "success",
            },
          );

          try {
            const freshDatasets = await getDatasets();
            const dataset = freshDatasets.find((d) => d.id === datasetId);

            if (dataset) {
              const enrichedDatasets = await enrichDatasetsWithInfo(
                freshDatasets,
                datasets,
              );
              setDatasets(enrichedDatasets);
              setSelectedDatasetId(datasetId);
            } else {
              await fetchDatasets();
              setSelectedDatasetId(datasetId);
            }
          } catch (error) {
            console.error(
              "Error fetching datasets after job completion:",
              error,
            );
            await fetchDatasets();
            setSelectedDatasetId(datasetId);
          }
        },
        (result) => {
          console.error(`Dataset job failed:`, result);
          enqueueSnackbar(
            t("datasets:error.failedToCreateDataset", {
              error: result.error || t("common:unknownError"),
            }),
            { variant: "error" },
          );

          setDatasets((prevDatasets) => {
            const datasetExists = prevDatasets.some((d) => d.id === datasetId);

            if (datasetExists) {
              deleteDataset(datasetId).catch((error) => {
                console.error("Error deleting failed dataset:", error);
              });

              return prevDatasets.filter((d) => d.id !== datasetId);
            }

            return prevDatasets;
          });

          setSelectedDatasetId(null);
          setStep(0);
          setSelectedOption(null);
        },
      );
    }
  };

  const handleEditDataset = async (id, newName) => {
    try {
      const updatedDataset = await updateDataset(id, { name: newName });
      setDatasets((prevDatasets) =>
        prevDatasets.map((dataset) =>
          dataset.id === id
            ? { ...dataset, name: updatedDataset.name }
            : dataset,
        ),
      );
      enqueueSnackbar(t("datasets:message.datasetUpdateSuccess"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update dataset:", error);
      if (error.response?.status === 409) {
        enqueueSnackbar(t("datasets:error.datasetNameExists"), {
          variant: "error",
        });
      } else if (error.response?.status === 422) {
        enqueueSnackbar(t("datasets:error.datasetNameEmpty"), {
          variant: "error",
        });
      } else {
        enqueueSnackbar(t("datasets:error.failedToUpdateDataset"), {
          variant: "error",
        });
      }
      throw error;
    }
  };

  const handleEditNotebook = async (id, newName) => {
    try {
      const updatedNotebook = await updateNotebook(id, { name: newName });
      setNotebooks((prevNotebooks) =>
        prevNotebooks.map((notebook) =>
          notebook.id === id
            ? { ...notebook, name: updatedNotebook.name }
            : notebook,
        ),
      );
      enqueueSnackbar(t("datasets:message.notebookUpdateSuccess"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update notebook:", error);
      if (error.response?.status === 422) {
        enqueueSnackbar(t("datasets:error.notebookNameEmpty"), {
          variant: "error",
        });
      } else if (error.response?.status === 304) {
        enqueueSnackbar(t("datasets:message.noChangesMade"), {
          variant: "info",
        });
      } else {
        enqueueSnackbar(t("datasets:error.failedToUpdateNotebook"), {
          variant: "error",
        });
      }
      throw error;
    }
  };

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
                        setStep(0);
                        setSelectedOption(null);
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
                        setStep(0);
                        setSelectedOption(null);
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
                      tourContextType="datasets"
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
