import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Divider,
  Button,
  ButtonGroup,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useParams, useNavigate } from "react-router-dom";
import { PlayArrow, TableChart, BarChart } from "@mui/icons-material";
import ModelComparisonTable from "./ModelComparisonTable";
import RunCard from "./RunCard";
import ModelCardCompact from "./ModelCardCompact";
import { getComponents } from "../../api/component";
import ResultsGraphs from "../../pages/results/components/ResultsGraphs";
import RetrainConfirmDialog from "./RetrainConfirmDialog";
import ModelsBreadcrumbs from "./ModelsBreadcrumbs";
import { useTranslation } from "react-i18next";

import { useModels } from "./ModelsContext";
import { useTourContext } from "../tour/TourProvider";
import { useRunScores } from "../../hooks/models/useRunScores";

export default function SessionVisualization() {
  const [models, setModels] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [highlightedRunId, setHighlightedRunId] = useState(null);
  const [showTable, setShowTable] = useState(true);
  const [metricSplit, setMetricSplit] = useState("test");
  const [explainerRefreshTrigger, setExplainerRefreshTrigger] = useState(0);
  const { t } = useTranslation(["models", "common"]);
  const sessionTourContext = useTourContext();
  const params = useParams();
  const navigate = useNavigate();

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
    selectModel,
  } = useModels();

  const { profiles, selectedProfile, setSelectedProfile, scores } =
    useRunScores({ session, runs, metricSplit });

  const theme = useTheme();
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const onStart = (e) => {
      if (e.dataTransfer.types.includes("application/x-dashai-model")) {
        setIsDragging(true);
      }
    };
    const onEnd = () => {
      setIsDragging(false);
      setIsDragOver(false);
    };
    window.addEventListener("dragstart", onStart);
    window.addEventListener("dragend", onEnd);
    return () => {
      window.removeEventListener("dragstart", onStart);
      window.removeEventListener("dragend", onEnd);
    };
  }, []);

  const handleToggleView = React.useCallback((isTable) => {
    setShowTable(isTable);
  }, []);

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
    setTimeout(() => setSelectedRunId(null), 2000);
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

  const activeRun = params.runId
    ? runs.find((r) => String(r.id) === params.runId)
    : null;

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
        onDragOver={(e) => {
          if (e.dataTransfer.types.includes("Files")) e.preventDefault();
          if (!e.dataTransfer.types.includes("application/x-dashai-model"))
            return;
          e.preventDefault();
          e.dataTransfer.dropEffect = "copy";
        }}
        onDragEnter={(e) => {
          if (e.dataTransfer.types.includes("Files")) e.preventDefault();
          if (!e.dataTransfer.types.includes("application/x-dashai-model"))
            return;
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={(e) => {
          const related = e.relatedTarget;
          if (!related || !e.currentTarget.contains(related)) {
            setIsDragOver(false);
          }
        }}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          try {
            const model = JSON.parse(
              e.dataTransfer.getData("application/x-dashai-model"),
            );
            if (model?.name) selectModel(model);
          } catch {
            // ignore invalid drops
          }
        }}
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "auto",
          position: "relative",
          outline: isDragOver
            ? `2px dashed ${theme.palette.primary.main}`
            : isDragging
              ? `2px dashed ${theme.palette.divider}`
              : "none",
          transition: "outline 0.15s",
        }}
      >
        {isDragging && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: isDragOver
                ? `${theme.palette.primary.main}14`
                : `${theme.palette.action.hover}`,
              pointerEvents: "none",
              transition: "background-color 0.15s",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color: isDragOver
                  ? theme.palette.primary.main
                  : theme.palette.text.secondary,
                fontWeight: 600,
                pointerEvents: "none",
                transition: "color 0.15s",
              }}
            >
              {t("models:label.dropModelHere")}
            </Typography>
          </Box>
        )}
        {/* TEMP scaffold for phase 1 (routing/breadcrumbs) — replaced by the
            full-screen model detail view in phase 3 */}
        {params.runId && (
          <Box sx={{ px: 4, pt: 4 }}>
            <ModelsBreadcrumbs />
          </Box>
        )}

        {/* Model detail (interim placeholder — full-screen layout lands in
            the last phase; for now this just keeps edit/train/results
            reachable while a specific run is selected via the URL) */}
        {params.runId ? (
          <Box sx={{ flex: 1, p: 4 }}>
            {activeRun ? (
              <RunCard
                run={activeRun}
                models={models}
                session={session}
                onTrain={handleTrainWithTour}
                onDelete={onDeleteRun}
                explainerRefreshTrigger={explainerRefreshTrigger}
                onOperationsRefresh={() =>
                  setExplainerRefreshTrigger((prev) => prev + 1)
                }
                existingRuns={runs}
                onRefresh={fetchRuns}
                forceExpanded
              />
            ) : (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                }}
              >
                <Typography variant="body1" color="text.secondary">
                  {t("models:label.runNotFound")}
                </Typography>
              </Box>
            )}
          </Box>
        ) : (
          <>
            {/* Compact model cards — quick access to each model */}
            <Box
              data-tour="run-cards-section"
              sx={{
                p: 4,
              }}
            >
              {runs.length === 0 ? (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minHeight: "50vh",
                  }}
                >
                  <Typography variant="body1" color="text.secondary">
                    {t("models:label.noRunsYet")}
                  </Typography>
                </Box>
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gap: 3,
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(240px, 1fr))",
                  }}
                >
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
                      <ModelCardCompact
                        run={run}
                        models={models}
                        score={scores[run.id]}
                        onTrain={handleTrainWithTour}
                        onDelete={onDeleteRun}
                        onOpen={() =>
                          navigate(
                            `/app/models/sessions/${session.id}/model/${run.id}`,
                          )
                        }
                        isHighlighted={highlightedRunId === run.id}
                      />
                    </Box>
                  ))}
                </Box>
              )}
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Comparison analysis area — table/graphs across all models */}
            <Box
              data-tour="model-comparison-panel"
              sx={{
                flexShrink: 0,
                p: 4,
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
                  mb: 2,
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
                        const notStartedRuns = runs.filter(
                          (r) => r.status === 0,
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
                    minHeight: "40vh",
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    {t("models:label.noRunsYet")}
                  </Typography>
                </Box>
              ) : showTable ? (
                <ModelComparisonTable
                  runs={runs}
                  session={session}
                  onTrain={onTrain}
                  onViewDetails={handleViewDetails}
                  onDelete={onDeleteRun}
                  onRowClick={handleRowClick}
                  metricSplit={metricSplit}
                  profiles={profiles}
                  selectedProfile={selectedProfile}
                  onProfileChange={setSelectedProfile}
                />
              ) : (
                <ResultsGraphs
                  runs={runs}
                  selectedSplit={metricSplit}
                  onSplitChange={setMetricSplit}
                />
              )}
            </Box>
          </>
        )}
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
