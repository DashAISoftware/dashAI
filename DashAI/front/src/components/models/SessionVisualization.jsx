import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Stack,
  Paper,
  Divider,
  Button,
  ButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import { PlayArrow, TableChart, BarChart } from "@mui/icons-material";
import JobQueueWidget from "../jobs/JobQueueWidget";
import { getRunStatus } from "../../utils/runStatus";
import ModelComparisonTable from "./ModelComparisonTable";
import RunCard from "./RunCard";
import { getComponents } from "../../api/component";
import ResultsGraphs from "../../pages/results/components/ResultsGraphs";
import NewGlobalExplainerModal from "../explainers/NewGlobalExplainerModal";
import NewLocalExplainerModal from "../explainers/NewLocalExplainerModal";
import { useTranslation } from "react-i18next";

export default function SessionVisualization({
  session,
  runs = [],
  onTrain,
  onEditRun,
  onDeleteRun,
}) {
  const [models, setModels] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [tableHeight, setTableHeight] = useState(280);
  const [showTable, setShowTable] = useState(true);
  const [previousTableHeight, setPreviousTableHeight] = useState(280);
  const [metricSplit, setMetricSplit] = useState("test");
  const [selectedRunForExplainer, setSelectedRunForExplainer] = useState(null);
  const [explainerDialogOpen, setExplainerDialogOpen] = useState(false);
  const [globalExplainerModalOpen, setGlobalExplainerModalOpen] =
    useState(false);
  const [localExplainerModalOpen, setLocalExplainerModalOpen] = useState(false);
  const [explainerRefreshTrigger, setExplainerRefreshTrigger] = useState(0);
  const isResizing = React.useRef(false);
  const { t } = useTranslation(["models", "common"]);

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

  const handleExplainer = React.useCallback((run) => {
    setSelectedRunForExplainer(run);
    setExplainerDialogOpen(true);
  }, []);

  const handleCloseExplainerDialog = () => {
    setExplainerDialogOpen(false);
  };

  const handleGlobalExplainer = () => {
    setGlobalExplainerModalOpen(true);
    setExplainerDialogOpen(false);
  };

  const handleLocalExplainer = () => {
    setLocalExplainerModalOpen(true);
    setExplainerDialogOpen(false);
  };

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

  const handleMouseMove = React.useCallback((e) => {
    if (isResizing.current) {
      const container = document.querySelector("[data-session-viz]");
      if (container) {
        const containerRect = container.getBoundingClientRect();
        const newHeight = e.clientY - containerRect.top;
        const minHeight = 150;
        const maxHeight = containerRect.height * 0.8;
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
            p: 4,
          }}
        >
          <Typography variant="h5" color="text.secondary">
            {t("models:label.noSessionSelected")}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            {t("models:label.selectSessionToViewModels")}
          </Typography>
        </Box>
        <JobQueueWidget />
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
        <Paper
          data-tour="model-comparison-panel"
          sx={{
            height: `${tableHeight}px`,
            flexShrink: 0,
            borderBottom: "1px solid",
            borderColor: "divider",
            p: 2,
            position: "relative",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography variant="h6">
              {t("models:label.modelComparison")}
            </Typography>
            <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
              {/* Metric Split Selector */}
              {showTable &&
                (hasTrainMetrics || hasValidationMetrics || hasTestMetrics) && (
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
              {runs.length > 0 &&
                runs.some((r) => getRunStatus(r.status) === "Not Started") && (
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<PlayArrow />}
                    onClick={() => {
                      const notStartedRuns = runs.filter(
                        (r) => getRunStatus(r.status) === "Not Started",
                      );
                      notStartedRuns.forEach((run) => onTrain(run));
                    }}
                  >
                    {t("models:button.runAll")}
                  </Button>
                )}
            </Box>
          </Box>
          {runs.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "calc(100% - 40px)",
              }}
            >
              <Typography variant="body2" color="text.secondary">
                {t("models:label.noRunsYet")}
              </Typography>
            </Box>
          ) : (
            <Box sx={{ height: "calc(100% - 40px)", overflow: "auto" }}>
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
                  runs={runs.map((run) => ({
                    ...run,
                    status:
                      typeof run.status === "number"
                        ? getRunStatus(run.status)
                        : run.status,
                  }))}
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
              bottom: -2,
              left: 0,
              right: 0,
              height: "5px",
              cursor: "row-resize",
              bgcolor: "transparent",
              transition: "background-color 0.2s ease",
              "&:hover": {
                bgcolor: "primary.main",
              },
              zIndex: 10,
            }}
          />
        </Paper>

        <Divider sx={{ my: 1, mt: 1 }} />

        {/* Scrollable Run Cards */}
        <Box
          data-tour="run-cards-section"
          sx={{
            flex: 1,
            overflow: "auto",
            p: 2,
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
            <Stack spacing={2}>
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
                    transition: "all 0.3s ease",
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
                    onTrain={onTrain}
                    onEdit={onEditRun}
                    onExplainer={handleExplainer}
                    onDelete={onDeleteRun}
                    explainerRefreshTrigger={explainerRefreshTrigger}
                    isLastRun={index === sortedRuns.length - 1}
                  />
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Box>

      {/* Explainer Type Selection Dialog */}
      <Dialog
        open={explainerDialogOpen}
        onClose={handleCloseExplainerDialog}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Select Explainer Type</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Button
              variant="outlined"
              fullWidth
              onClick={handleGlobalExplainer}
              size="large"
            >
              {t("models:label.globalExplainer")}
            </Button>
            <Button
              variant="outlined"
              fullWidth
              onClick={handleLocalExplainer}
              size="large"
            >
              {t("models:label.localExplainer")}
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseExplainerDialog}>
            {t("common:cancel")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Global Explainer Modal */}
      <NewGlobalExplainerModal
        open={globalExplainerModalOpen}
        setOpen={setGlobalExplainerModalOpen}
        explainerConfig={{
          runId: selectedRunForExplainer?.id,
          taskName: session?.task_name,
        }}
        onExplainerCreated={() => {
          setExplainerRefreshTrigger((prev) => prev + 1);
        }}
      />

      {/* Local Explainer Modal */}
      <NewLocalExplainerModal
        open={localExplainerModalOpen}
        setOpen={setLocalExplainerModalOpen}
        explainerConfig={{
          runId: selectedRunForExplainer?.id,
          sessionId: session?.id,
          taskName: session?.task_name,
        }}
        onExplainerCreated={() => {
          setExplainerRefreshTrigger((prev) => prev + 1);
        }}
      />

      <JobQueueWidget />
    </>
  );
}

SessionVisualization.propTypes = {
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  runs: PropTypes.array,
  onTrain: PropTypes.func.isRequired,
  onEditRun: PropTypes.func.isRequired,
  onDeleteRun: PropTypes.func.isRequired,
};
