import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Divider,
  Button,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useParams, useNavigate } from "react-router-dom";
import { PlayArrow } from "@mui/icons-material";
import ModelComparisonTable from "./ModelComparisonTable";
import ModelDetailView from "./ModelDetailView";
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
  const [metricSplit, setMetricSplit] = useState("test");
  const { t } = useTranslation(["models", "common"]);
  const sessionTourContext = useTourContext();
  const params = useParams();
  const navigate = useNavigate();

  const {
    selectedSession: session,
    runs,
    datasets,
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
    explainerRefreshTrigger,
    triggerExplainerRefresh,
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

  // Scroll to a newly added run card and mark it to be highlighted
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
    return () => clearTimeout(scrollTimer);
  }, [lastAddedRunId]);

  // Clear the highlight a few seconds after it was set. Kept in its own
  // effect (keyed on highlightedRunId, not lastAddedRunId) so it isn't
  // cancelled by clearLastAddedRunId() re-triggering the effect above.
  useEffect(() => {
    if (!highlightedRunId) return;
    const clearTimer = setTimeout(() => setHighlightedRunId(null), 1000);
    return () => clearTimeout(clearTimer);
  }, [highlightedRunId]);

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

  const datasetName = datasets.find((d) => d.id === session?.dataset_id)?.name;

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

  // If the run being deleted is the one currently open in the detail view,
  // navigate back to the session overview instead of leaving the user on a
  // "run not found" screen for a run that no longer exists.
  const handleDeleteRun = async (run) => {
    await onDeleteRun(run);
    if (params.runId && String(run.id) === params.runId) {
      navigate(`/app/models/sessions/${session.id}`);
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
        {/* Model detail: full-screen view for a single run */}
        {params.runId ? (
          activeRun ? (
            <ModelDetailView
              run={activeRun}
              models={models}
              session={session}
              datasetName={datasetName}
              onTrain={handleTrainWithTour}
              onDelete={handleDeleteRun}
              explainerRefreshTrigger={explainerRefreshTrigger}
              onOperationsRefresh={triggerExplainerRefresh}
              existingRuns={runs}
              onRefresh={fetchRuns}
            />
          ) : (
            <Box sx={{ px: 4, pt: 4 }}>
              <ModelsBreadcrumbs />
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  py: 8,
                }}
              >
                <Typography variant="body1" color="text.secondary">
                  {t("models:label.runNotFound")}
                </Typography>
              </Box>
            </Box>
          )
        ) : (
          <>
            {/* Session header: breadcrumb, title, quick stats */}
            <Box sx={{ px: 4, pt: 4 }}>
              <ModelsBreadcrumbs />
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-end",
                  flexWrap: "wrap",
                  gap: 2,
                }}
              >
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
                    {session.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("models:label.modelCount", {
                      count: sortedRuns.length,
                    })}
                    {datasetName && ` | ${t("common:dataset")} ${datasetName}`}
                  </Typography>
                </Box>

                {runs.length > 0 && (
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<PlayArrow />}
                    disabled={!runs.some((r) => r.status === 0)}
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

            {/* Compact model cards: quick access to each model */}
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
                      "repeat(auto-fill, minmax(340px, 1fr))",
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
                        session={session}
                        existingRuns={runs}
                        onTrain={handleTrainWithTour}
                        onDelete={handleDeleteRun}
                        onRefresh={fetchRuns}
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

            {/* Comparison analysis area: table/graphs across all models */}
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
                  {/* Metric Split Selector: controls both table and graph views */}
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
              ) : (
                <>
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

                  <Typography
                    variant="h6"
                    color="text.primary"
                    sx={{ mt: 6, mb: 2 }}
                  >
                    {t("common:graphs")}
                  </Typography>
                  <ResultsGraphs
                    runs={runs}
                    selectedSplit={metricSplit}
                    onSplitChange={setMetricSplit}
                  />
                </>
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
