import { useState, useEffect, useRef, useCallback } from "react";
import { Box, IconButton } from "@mui/material";
import { ChevronLeft, ChevronRight } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import LeftBar from "../../components/models/LeftBar";
import CenterBox from "../../components/threeSectionLayout/CenterBox";
import RightBar from "../../components/models/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import CreateSessionSteps from "../../components/models/CreateSessionSteps";
import SessionVisualization from "../../components/models/SessionVisualization";
import DatasetVisualization from "../../components/models/DatasetVisualization";
import AddModelDialog from "../../components/models/AddModelDialog";
import { getComponents } from "../../api/component";
import { getDatasets, getDatasetInfo } from "../../api/datasets";
import {
  getExperiments,
  updateExperiment,
  deleteExperiment,
} from "../../api/experiment";
import {
  getRuns,
  deleteRun,
  updateRunParameters,
  resetRunById,
  getRunById,
} from "../../api/run";
import { enqueueRunnerJob as enqueueRunnerJobRequest } from "../../api/job";
import { startJobPolling } from "../../utils/jobPoller";
import { getRunStatus } from "../../utils/runStatus";

export default function ModelsContent() {
  const [step, setStep] = useState(0);
  const [leftBarVisible, setLeftBarVisible] = useState(true);
  const [rightBarVisible, setRightBarVisible] = useState(true);
  const [leftBarWidth, setLeftBarWidth] = useState(20);
  const [rightBarWidth, setRightBarWidth] = useState(20);
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [runs, setRuns] = useState([]);
  const [addModelDialogOpen, setAddModelDialogOpen] = useState(false);
  const [preselectedModel, setPreselectedModel] = useState(null);
  const [trackedJobIds, setTrackedJobIds] = useState(new Set());

  const isResizingLeft = useRef(false);
  const isResizingRight = useRef(false);
  const [isTogglingLeft, setIsTogglingLeft] = useState(false);
  const [isTogglingRight, setIsTogglingRight] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const data = await getComponents({
          selectTypes: ["Task"],
          hasRelatedOfType: "Model",
        });
        setTasks(data);
      } catch (error) {
        enqueueSnackbar("Failed to fetch tasks", {
          variant: "error",
        });
        console.error("Failed to fetch tasks:", error);
      }
    };
    fetchTasks();
  }, []);

  const enrichDatasetsWithInfo = async (newDatasets, existingDatasets = []) => {
    const enrichedDatasets = await Promise.all(
      newDatasets.map(async (dataset) => {
        const existingDataset = existingDatasets.find(
          (d) => d.id === dataset.id,
        );
        if (
          existingDataset &&
          existingDataset.description &&
          existingDataset.description.includes("rows,")
        ) {
          return {
            ...dataset,
            description: existingDataset.description,
          };
        }

        try {
          const info = await getDatasetInfo(dataset.id);
          return {
            ...dataset,
            description: `${info.total_rows} rows, ${info.total_columns} columns`,
          };
        } catch (error) {
          console.warn(
            `Failed to fetch info for dataset ${dataset.id}:`,
            error,
          );
          return {
            ...dataset,
            description: dataset.description || "",
          };
        }
      }),
    );
    return enrichedDatasets;
  };

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const data = await getDatasets();
        const enrichedData = await enrichDatasetsWithInfo(data, []);
        setDatasets(enrichedData);
      } catch (error) {
        enqueueSnackbar("Failed to fetch datasets", {
          variant: "error",
        });
        console.error("Failed to fetch datasets:", error);
      }
    };
    fetchDatasets();
  }, []);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await getExperiments();
        setSessions(data);
      } catch (error) {
        enqueueSnackbar("Failed to fetch sessions", {
          variant: "error",
        });
        console.error("Failed to fetch sessions:", error);
      }
    };
    fetchSessions();
  }, []);

  const fetchRuns = useCallback(async () => {
    if (!selectedSessionId) return;
    try {
      const data = await getRuns(selectedSessionId.toString());
      const runsWithStatus = data.map((run) => ({
        ...run,
        status:
          typeof run.status === "number"
            ? run.status
            : getRunStatus(run.status),
      }));
      setRuns(runsWithStatus);
    } catch (error) {
      enqueueSnackbar("Failed to fetch runs", {
        variant: "error",
      });
      console.error("Failed to fetch runs:", error);
    }
  }, [selectedSessionId, enqueueSnackbar]);

  // Fetch runs when session is selected
  useEffect(() => {
    if (selectedSessionId) {
      fetchRuns();
    } else {
      setRuns([]);
      setSelectedSession(null);
    }
  }, [selectedSessionId, fetchRuns]);

  // Update selected session object when sessions or selectedSessionId changes
  useEffect(() => {
    if (selectedSessionId && sessions.length > 0) {
      const session = sessions.find((s) => s.id === selectedSessionId);
      setSelectedSession(session || null);
    }
  }, [selectedSessionId, sessions]);

  const handleTaskSelect = (taskName) => {
    const task = tasks.find((t) => t.name === taskName);
    setSelectedTask(task);
    setStep(1);
  };

  const handleBackToTaskSelection = () => {
    setSelectedTask(null);
    setStep(0);
  };

  const handleSessionCreated = (newSession) => {
    setSessions((prev) => [...prev, newSession]);
    setSelectedSessionId(newSession.id);
  };

  const handleSessionClick = (sessionId) => {
    setSelectedSessionId(sessionId);
  };

  const handleDatasetClick = (datasetId) => {
    setSelectedDatasetId(datasetId);
    setSelectedSessionId(null);
  };

  const handleSessionDelete = async (sessionId) => {
    try {
      await deleteExperiment(sessionId.toString());
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
        setSelectedSession(null);
      }
      enqueueSnackbar("Session deleted successfully", { variant: "success" });
    } catch (error) {
      enqueueSnackbar("Failed to delete session", { variant: "error" });
      console.error("Failed to delete session:", error);
    }
  };

  const handleModelClick = (model) => {
    if (!selectedSession) {
      enqueueSnackbar("Please select a session first", { variant: "warning" });
      return;
    }
    setPreselectedModel(model.name);
    setAddModelDialogOpen(true);
  };

  const handleRunCreated = (newRun) => {
    setRuns((prev) => [...prev, newRun]);
    enqueueSnackbar(`Run "${newRun.name}" added to session`, {
      variant: "success",
    });
  };

  const handleTrainRun = async (run) => {
    try {
      // Reset the run first
      const updatedRun = await resetRunById(run.id.toString());

      // Enqueue the training job
      const response = await enqueueRunnerJobRequest(run.id);

      if (!response || !response.id) {
        enqueueSnackbar(`Error starting run ${run.name}`, {
          variant: "error",
        });
        return;
      }

      enqueueSnackbar(`Training started for "${run.name}"`, {
        variant: "success",
      });

      // Update local state to show running status
      setRuns((prevRuns) =>
        prevRuns.map((r) =>
          r.id === run.id
            ? { ...updatedRun, status: 1 } // 1 = Delivered
            : r,
        ),
      );

      // Track job and start polling
      setTrackedJobIds((prev) => new Set(prev).add(response.id));

      startJobPolling(
        response.id,
        async () => {
          // Job completed - fetch updated run
          const updated = await getRunById(run.id.toString());
          setRuns((prevRuns) =>
            prevRuns.map((r) => (r.id === run.id ? updated : r)),
          );
          enqueueSnackbar(`Run "${run.name}" completed`, {
            variant: "success",
          });
        },
        async (result) => {
          // Job failed - fetch updated run
          const updated = await getRunById(run.id.toString());
          setRuns((prevRuns) =>
            prevRuns.map((r) => (r.id === run.id ? updated : r)),
          );
          enqueueSnackbar(
            `Run "${run.name}" failed: ${result.error || "Unknown error"}`,
            { variant: "error" },
          );
        },
      );
    } catch (error) {
      console.error("Error training run:", error);
      enqueueSnackbar(`Error starting run "${run.name}"`, {
        variant: "error",
      });
    }
  };

  const handleEditRun = async (run) => {
    // TODO: Open edit dialog with run parameters
    console.log("Edit run:", run);
    enqueueSnackbar("Edit functionality coming soon", { variant: "info" });
  };

  const handleRetryRun = async (run) => {
    await handleTrainRun(run);
  };

  const handleDeleteRun = async (run) => {
    try {
      await deleteRun(run.id.toString());
      setRuns((prev) => prev.filter((r) => r.id !== run.id));
      enqueueSnackbar(`Run "${run.name}" deleted successfully`, {
        variant: "success",
      });
    } catch (error) {
      console.error("Error deleting run:", error);
      enqueueSnackbar(`Error deleting run "${run.name}"`, {
        variant: "error",
      });
    }
  };

  const handleSessionEdit = async (sessionId, newName) => {
    try {
      const result = await updateExperiment({
        id: sessionId,
        formData: { name: newName },
      });
      console.log("Update result:", result);
      setSessions((prev) =>
        prev.map((session) =>
          session.id === sessionId ? { ...session, name: newName } : session,
        ),
      );
      enqueueSnackbar("Session renamed successfully", { variant: "success" });
    } catch (error) {
      enqueueSnackbar("Failed to rename session", { variant: "error" });
      console.error("Failed to rename session:", error);
    }
  };

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    setSelectedDatasetId(null);
    setSelectedTask(null);
    setStep(0);
  };

  const handleMouseMove = useCallback((e) => {
    if (isResizingLeft.current) {
      const container = document.querySelector('[data-container="models"]');
      const containerRect = container.getBoundingClientRect();
      const newWidth =
        ((e.clientX - containerRect.left) / containerRect.width) * 100;
      if (newWidth >= 15 && newWidth <= 40) {
        setLeftBarWidth(newWidth);
      }
    }

    if (isResizingRight.current) {
      const container = document.querySelector('[data-container="models"]');
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

  return (
    <Box
      height="calc(100vh - 74px)"
      width="100%"
      display="flex"
      data-container="models"
    >
      {/* Left Panel */}
      <Box
        width={leftBarVisible ? `${leftBarWidth}%` : "0%"}
        position="relative"
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
              selectedDatasetId={selectedDatasetId}
              sessions={sessions}
              selectedSessionId={selectedSessionId}
              tasks={tasks}
              onDatasetClick={handleDatasetClick}
              onSessionClick={handleSessionClick}
              onSessionDelete={handleSessionDelete}
              onSessionEdit={handleSessionEdit}
              onToggle={handleToggleLeft}
              handleNewSessionButton={handleNewSessionButton}
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

      {/* Center Panel */}
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
          {selectedSessionId ? (
            <SessionVisualization
              session={selectedSession}
              runs={runs}
              onTrain={handleTrainRun}
              onEditRun={handleEditRun}
              onRetryRun={handleRetryRun}
              onDeleteRun={handleDeleteRun}
            />
          ) : selectedDatasetId ? (
            <DatasetVisualization
              dataset={datasets.find((d) => d.id === selectedDatasetId)}
            />
          ) : step === 0 ? (
            <SelectOptionMenu
              title="Models Module"
              subtitle="Configure tasks, train and compare models in organized sessions. Select a task to begin your modeling workflow."
              options={tasks.map((task) => ({
                name: task.name,
                display_name:
                  task.metadata?.display_name ||
                  task.name
                    .replace("Task", "")
                    .replace(/([A-Z])/g, " $1")
                    .trim(),
                description:
                  task.description || task.metadata?.short_description || "",
                Icon: null,
              }))}
              searchBar={true}
              goToNextStep={handleTaskSelect}
            />
          ) : step === 1 && selectedTask ? (
            <CreateSessionSteps
              backHome={handleBackToTaskSelection}
              selectedTask={selectedTask}
              datasets={datasets}
              handleSessionCreated={handleSessionCreated}
              existingSessions={sessions}
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

      {/* Right Panel */}
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
              session={selectedSession}
              onToggle={handleToggleRight}
              onModelClick={handleModelClick}
            />
          </>
        )}
      </Box>

      {/* Add Model Dialog */}
      <AddModelDialog
        open={addModelDialogOpen}
        onClose={() => {
          setAddModelDialogOpen(false);
          setPreselectedModel(null);
        }}
        session={selectedSession}
        preselectedModel={preselectedModel}
        existingRuns={runs}
        onRunCreated={handleRunCreated}
      />
    </Box>
  );
}
