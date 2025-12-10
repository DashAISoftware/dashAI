import { useState, useEffect, useRef, useCallback } from "react";
import { Box, IconButton } from "@mui/material";
import { ChevronLeft, ChevronRight } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import LeftBar from "../../components/models/LeftBar";
import CenterBox from "../../components/threeSectionLayout/CenterBox";
import RightBar from "../../components/models/RightBar";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import CreateSessionSteps from "../../components/models/CreateSessionSteps";
import { getComponents } from "../../api/component";
import { getDatasets } from "../../api/datasets";
import { getExperiments } from "../../api/experiment";

export default function ModelsContent() {
  const [step, setStep] = useState(0);
  const [leftBarVisible, setLeftBarVisible] = useState(true);
  const [rightBarVisible, setRightBarVisible] = useState(true);
  const [leftBarWidth, setLeftBarWidth] = useState(20);
  const [rightBarWidth, setRightBarWidth] = useState(20);
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [sessions, setSessions] = useState([]);

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

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const data = await getDatasets();
        setDatasets(data);
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
            <LeftBar onToggle={handleToggleLeft} />
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
          {step === 0 ? (
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
            <RightBar onToggle={handleToggleRight} />
          </>
        )}
      </Box>
    </Box>
  );
}
