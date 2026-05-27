import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Button,
  ButtonGroup,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  PlayArrow,
  TableChart,
  BarChart,
  ExpandMore,
} from "@mui/icons-material";
import ModelComparisonTable from "./ModelComparisonTable";
import RunCard from "./RunCard";
import { getComponents } from "../../api/component";
import ResultsGraphs from "../../pages/results/components/ResultsGraphs";
import RetrainConfirmDialog from "./RetrainConfirmDialog";
import { useTranslation } from "react-i18next";

import { useModels } from "./ModelsContext";
import { useTourContext } from "../tour/TourProvider";

export default function SessionVisualization() {
  const [models, setModels] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [highlightedRunId, setHighlightedRunId] = useState(null);
  const [tableHeight, setTableHeight] = useState(280);
  const [showTable, setShowTable] = useState(true);
  const [previousTableHeight, setPreviousTableHeight] = useState(280);
  const [metricSplit, setMetricSplit] = useState("test");
  const [tableCollapsed, setTableCollapsed] = useState(false);
  const [explainerRefreshTrigger, setExplainerRefreshTrigger] = useState(0);
  const isResizing = React.useRef(false);
  const { t } = useTranslation(["models", "common"]);
  const sessionTourContext = useTourContext();

  const {
    selectedSession: session,
    runs,
    onTrainRun: onTrain,
    onDeleteRun,
    fetchRuns,
    retrainDialogOpen,
    runToRetrain,
    operationsCount,
    handleCancelRetrain,
    handleConfirmRetrain,
    lastAddedRunId,
    clearLastAddedRunId,
  } = useModels();

  const theme = useTheme();

  // Auto-expand when switching to graphs
  const handleToggleView = React.useCallback(
    (isTable) => {
      if (!isTable && showTable) {
        // Switching from Table to Graphs
        setPreviousTableHeight(tableHeight);
        setTableHeight(Math.max(tableHeight, 600));
      } else if (isTable && !showTable) {
        // Switching from Graphs to Table
        setTableHeight(previousTableHeight);
      }
      setShowTable(isTable);
    },
    [showTable, tableHeight, previousTableHeight],
  );

  const fetchModels = React.useCallback(async () => {
    try {
      const response = await getComponents({ selectTypes: ["Model"] });
      setModels(response);
    } catch (error) {
      console.error("Error fetching models:", error);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  useEffect(() => {
    const handleGraphsButtonClick = (e) => {
      const graphsButton = e.target.closest('[data-tour="graphs-button"]');
      if (graphsButton && sessionTourContext?.stepIndex === 7) {
        setTimeout(() => {
          sessionTourContext.nextStep();
        }, 500);
      }
    };

    document.addEventListener("click", handleGraphsButtonClick, true);
    return () => {
      document.removeEventListener("click", handleGraphsButtonClick, true);
    };
  }, [sessionTourContext]);

  // Check if tour should start from previous tutorial
  useEffect(() => {
    const shouldStartTour = sessionStorage.getItem("startModelsSessionTour");
    if (shouldStartTour === "true" && sessionTourContext) {
      sessionStorage.removeItem("startModelsSessionTour");
      setTimeout(() => {
        sessionTourContext.startTour();
      }, 1000);
    }
  }, [sessionTourContext]);

  // Scroll to and highlight a newly added run card
  useEffect(() => {
    if (!lastAddedRunId) return;
    const scrollTimer = setTimeout(() => {
      const element = document.getElementById(`run-card-${lastAddedRunId}`);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
      setHighlightedRunId(lastAddedRunId);
      clearLastAddedRunId();
    }, 100);
    const clearTimer = setTimeout(() => setHighlightedRunId(null), 4100);
    return () => {
      clearTimeout(scrollTimer);
      clearTimeout(clearTimer);
    };
  }, [lastAddedRunId]);

  const handleRowClick = React.useCallback((runId) => {
    setSelectedRunId(runId);
    const element = document.getElementById(`run-card-${runId}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  const handleViewDetails = React.useCallback((run) => {
    if (!run?.id) return;
    setSelectedRunId(run.id);
    const element = document.getElementById(`run-card-${run.id}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  const sortedRuns = React.useMemo(
    () => [...runs].sort((a, b) => new Date(a.created) - new Date(b.created)),
    [runs],
  );

  // Check which metrics are available
  const hasTrainMetrics = runs.some(
    (run) => run.train_metrics && Object.keys(run.train_metrics).length > 0,
  );
  const hasValidationMetrics = runs.some(
    (run) =>
      run.validation_metrics && Object.keys(run.validation_metrics).length > 0,
  );
  const hasTestMetrics = runs.some(
    (run) => run.test_metrics && Object.keys(run.test_metrics).length > 0,
  );

  const handleTrainWithTour = (run) => {
    if (onTrain) onTrain(run);
    if (sessionTourContext?.run && sessionTourContext?.stepIndex === 5) {
      setTimeout(() => {
        sessionTourContext.nextStep();
      }, 500);
    }
  };

  const handleMouseMove = React.useCallback((e) => {
    if (isResizing.current) {
      const details = document.querySelector("[data-accordion-details]");
      if (details) {
        const detailsRect = details.getBoundingClientRect();
        const newHeight = e.clientY - detailsRect.top;
        const minHeight = 150;
        const maxHeight = window.innerHeight * 0.7;
        const clampedHeight = Math.max(
          minHeight,
          Math.min(maxHeight, newHeight),
        );
        setTableHeight(clampedHeight);
      }
    }
  }, []);

  const handleMouseUp = React.useCallback(() => {
    isResizing.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, []);

  React.useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  if (!session) {
    return (
      <>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
            justifyContent: "center",
            alignItems: "center",
            p: 8,
          }}
        >
          <Typography variant="h5" color="text.secondary">
            {t("models:label.noSessionSelected")}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 4 }}>
            {t("models:label.selectSessionToViewModels")}
          </Typography>
        </Box>
      </>
    );
  }

  return (
    <>
      <Box
        data-session-viz
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "hidden",
        }}
      >
        {/* Sticky Comparison Table */}
        <Accordion
          data-tour="model-comparison-panel"
          expanded={!tableCollapsed}
          onChange={() => setTableCollapsed((v) => !v)}
          disableGutters
          elevation={1}
          sx={{
            flexShrink: 0,
            borderBottom: "1px solid",
            borderColor: "divider",
            borderRadius: "4px",
            "&:before": { display: "none" },
          }}
        >
          <AccordionSummary
            expandIcon={
              <Tooltip
                title={
                  tableCollapsed ? t("common:expand") : t("common:collapse")
                }
              >
                <ExpandMore />
              </Tooltip>
            }
            sx={{
              alignItems: "flex-start",
              "& .MuiAccordionSummary-content": { my: "8px", mr: 1 },
              "& .MuiAccordionSummary-expandIconWrapper": { mt: "10px" },
            }}
          >
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                width: "100%",
                flexWrap: "wrap",
                gap: 1,
              }}
            >
              <Typography variant="h6" color="text.primary">
                {t("models:label.modelComparison")}
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  gap: 4,
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* Metric Split Selector — controls both table and graph views */}
                {(hasTrainMetrics ||
                  hasValidationMetrics ||
                  hasTestMetrics) && (
                  <ToggleButtonGroup
                    value={metricSplit}
                    exclusive
                    onChange={(e, newValue) => {
                      if (newValue !== null) setMetricSplit(newValue);
                    }}
                    size="small"
                  >
                    {hasTrainMetrics && (
                      <ToggleButton value="train">
                        {t("common:train")}
                      </ToggleButton>
                    )}
                    {hasValidationMetrics && (
                      <ToggleButton value="validation">
                        {t("common:validation")}
                      </ToggleButton>
                    )}
                    {hasTestMetrics && (
                      <ToggleButton value="test">
                        {t("common:test")}
                      </ToggleButton>
                    )}
                  </ToggleButtonGroup>
                )}

                {/* Toggle between Table and Graphs */}
                <ButtonGroup size="small" variant="outlined">
                  <Button
                    variant={showTable ? "contained" : "outlined"}
                    onClick={() => handleToggleView(true)}
                    startIcon={<TableChart />}
                  >
                    {t("common:table")}
                  </Button>
                  <Button
                    data-tour="graphs-button"
                    variant={!showTable ? "contained" : "outlined"}
                    onClick={() => handleToggleView(false)}
                    startIcon={<BarChart />}
                  >
                    {t("common:graphs")}
                  </Button>
                </ButtonGroup>

                {/* Run All Button */}
                {runs.length > 0 && runs.some((r) => r.status === 0) && (
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<PlayArrow />}
                    onClick={() => {
                      const notStartedRuns = runs.filter((r) => r.status === 0);
                      notStartedRuns.forEach((run) => onTrain(run));
                    }}
                  >
                    {t("models:button.runAll")}
                  </Button>
                )}
              </Box>
            </Box>
          </AccordionSummary>

          <AccordionDetails
            data-accordion-details
            sx={{
              p: 2,
              pt: 0,
              height: `${tableHeight}px`,
              overflow: "hidden",
              position: "relative",
            }}
          >
            {runs.length === 0 ? (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  {t("models:label.noRunsYet")}
                </Typography>
              </Box>
            ) : (
              <Box sx={{ height: "100%", overflow: "auto" }}>
                {showTable ? (
                  <ModelComparisonTable
                    runs={runs}
                    session={session}
                    onTrain={onTrain}
                    onViewDetails={handleViewDetails}
                    onDelete={onDeleteRun}
                    onRowClick={handleRowClick}
                    metricSplit={metricSplit}
                  />
                ) : (
                  <ResultsGraphs
                    runs={runs}
                    selectedSplit={metricSplit}
                    onSplitChange={setMetricSplit}
                  />
                )}
              </Box>
            )}

            {/* Resize Handle */}
            <Box
              onMouseDown={() => {
                isResizing.current = true;
                document.body.style.cursor = "row-resize";
                document.body.style.userSelect = "none";
              }}
              sx={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: "5px",
                cursor: "row-resize",
                bgcolor: "transparent",
                transition: "background-color 0.2s ease",
                "&:hover": { bgcolor: "primary.main" },
                zIndex: 10,
              }}
            />
          </AccordionDetails>
        </Accordion>

        <Divider sx={{ my: 2, mt: 2 }} />

        {/* Scrollable Run Cards */}
        <Box
          data-tour="run-cards-section"
          sx={{
            flex: 1,
            overflow: "auto",
            p: 4,
          }}
        >
          {runs.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              }}
            >
              <Typography variant="body1" color="text.secondary">
                {t("models:label.noRunsYet")}
              </Typography>
            </Box>
          ) : (
            <Stack spacing={4}>
              {sortedRuns.map((run, index) => (
                <Box
                  key={run.id}
                  id={`run-card-${run.id}`}
                  data-tour={
                    index === sortedRuns.length - 1
                      ? "first-run-card"
                      : undefined
                  }
                  sx={{
                    scrollMarginTop: "20px",
                    scrollMarginBottom: "20px",
                    transition: "transform 0.3s ease",
                    ...(selectedRunId === run.id && {
                      transform: "scale(1.02)",
                      boxShadow: 3,
                    }),
                  }}
                >
                  <RunCard
                    run={run}
                    models={models}
                    session={session}
                    onTrain={handleTrainWithTour}
                    onDelete={onDeleteRun}
                    explainerRefreshTrigger={explainerRefreshTrigger}
                    onOperationsRefresh={() =>
                      setExplainerRefreshTrigger((prev) => prev + 1)
                    }
                    isLastRun={index === sortedRuns.length - 1}
                    existingRuns={runs}
                    onRefresh={fetchRuns}
                    isHighlighted={highlightedRunId === run.id}
                  />
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Box>

      <RetrainConfirmDialog
        open={retrainDialogOpen}
        onClose={handleCancelRetrain}
        onConfirm={handleConfirmRetrain}
        run={runToRetrain}
        operationsCount={operationsCount}
      />
    </>
  );
}
