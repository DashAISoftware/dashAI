import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Button,
  Chip,
  Stack,
  Collapse,
  Tabs,
  Tab,
  Grid,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Add as AddIcon,
  TrendingUp as TrendingUpIcon,
  Close as CloseIcon,
} from "@mui/icons-material";
import ExplainersCard from "../explainers/ExplainersCard";
import PredictionCard from "./PredictionCard";
import InlineExplainerCreator from "../explainers/InlineExplainerCreator";
import DatasetPredictionPanel from "./DatasetPredictionPanel";
import ManualPredictionPanel from "./ManualPredictionPanel";
import LiveMetricsChart from "./LiveMetricsChart";
import HyperparameterPlots from "./HyperparameterPlots";
import { getExplainers } from "../../api/explainer";
import { getPredictions } from "../../api/predict";
import { checkHowManyOptimazers } from "../../utils/schema";
import { useTranslation } from "react-i18next";
import TimestampWrapper from "../shared/TimestampWrapper";
import { TIMESTAMP_KEYS } from "../../constants/timestamp";

export default function RunResults({
  run,
  session,
  onRefresh,
  explainerRefreshTrigger,
}) {
  const [globalExplainers, setGlobalExplainers] = useState([]);
  const [localExplainers, setLocalExplainers] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [resultsVisible, setResultsVisible] = useState(() => {
    const saved = localStorage.getItem(`run-${run.id}-results-visible`);
    return saved ? JSON.parse(saved) : false;
  });
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem(`run-${run.id}-active-tab`);
    return saved ? JSON.parse(saved) : 0;
  });

  const [globalCreatorOpen, setGlobalCreatorOpen] = useState(false);
  const [localCreatorOpen, setLocalCreatorOpen] = useState(false);
  const [globalExpanded, setGlobalExpanded] = useState(true);
  const [localExpanded, setLocalExpanded] = useState(true);
  const [datasetExpanded, setDatasetExpanded] = useState(true);
  const [manualExpanded, setManualExpanded] = useState(true);
  const [showDatasetPanel, setShowDatasetPanel] = useState(false);
  const [showManualPanel, setShowManualPanel] = useState(false);

  const optimizables = checkHowManyOptimazers({ params: run.parameters });
  const isFinished = run.status === 3;
  const isRunning = run.status === 1 || run.status === 2;
  const { t } = useTranslation(["models", "common"]);

  const runId = run.id;
  const fetchOperations = useCallback(async () => {
    if (!runId) return;

    try {
      const [globalExpls, localExpls, preds] = await Promise.all([
        getExplainers(runId, "global").catch(() => []),
        getExplainers(runId, "local").catch(() => []),
        getPredictions(runId).catch(() => []),
      ]);

      setGlobalExplainers(globalExpls);
      setLocalExplainers(localExpls);
      setPredictions(preds);
    } catch (error) {
      console.error("Error fetching operations:", error);
    }
  }, [runId]);

  useEffect(() => {
    fetchOperations();
  }, [fetchOperations, explainerRefreshTrigger]);

  // Refetch when run parameters change (after editing)
  useEffect(() => {
    fetchOperations();
  }, [
    run.parameters,
    run.optimizer_parameters,
    run.goal_metric,
    fetchOperations,
  ]);

  const hasRunningExplainers =
    globalExplainers.some((e) => e.status === 1 || e.status === 2) ||
    localExplainers.some((e) => e.status === 1 || e.status === 2);

  useEffect(() => {
    if (!hasRunningExplainers) return;
    const interval = setInterval(fetchOperations, 3000);
    return () => clearInterval(interval);
  }, [hasRunningExplainers, fetchOperations]);

  useEffect(() => {
    const handleOpenDialog = (event) => {
      if (event.detail.runId === run.id) {
        setResultsVisible(true);
        setActiveTab(2);
        setShowDatasetPanel(true);
      }
    };
    window.addEventListener("openPredictionDialog", handleOpenDialog);
    return () =>
      window.removeEventListener("openPredictionDialog", handleOpenDialog);
  }, [run.id]);

  useEffect(() => {
    if (isRunning) {
      setResultsVisible(true);
      setActiveTab(0); // Live Metrics tab
    }
  }, [isRunning]);

  useEffect(() => {
    localStorage.setItem(
      `run-${run.id}-results-visible`,
      JSON.stringify(resultsVisible),
    );
  }, [resultsVisible, run.id]);

  useEffect(() => {
    localStorage.setItem(`run-${run.id}-active-tab`, JSON.stringify(activeTab));
  }, [activeTab, run.id]);

  const handleExplainerCreated = () => {
    fetchOperations();
    if (onRefresh) onRefresh();
  };

  const handlePredictionCreated = (prediction) => {
    if (prediction) {
      setPredictions((prev) => {
        const index = prev.findIndex((p) => p.id === prediction.id);
        if (index === -1) {
          return [prediction, ...prev];
        }

        const updated = [...prev];
        updated[index] = prediction;
        return updated;
      });
    } else {
      fetchOperations();
    }

    if (onRefresh) onRefresh();
  };

  const handleExplainerDeleted = () => {
    fetchOperations();
    if (onRefresh) onRefresh();
  };

  const handlePredictionDeleted = () => {
    fetchOperations();
    if (onRefresh) onRefresh();
  };

  const totalOperations =
    globalExplainers.length + localExplainers.length + predictions.length;

  return (
    <Box id={`run-results-${run.id}`}>
      <Box sx={{ mb: 2 }}>
        <Button
          size="small"
          onClick={() => setResultsVisible(!resultsVisible)}
          endIcon={resultsVisible ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{ textTransform: "none" }}
        >
          {resultsVisible
            ? t("models:label.hideResults")
            : t("models:label.showResults")}
          {isFinished && (
            <Chip label={totalOperations} size="small" sx={{ ml: 1 }} />
          )}
        </Button>
      </Box>

      <Collapse in={resultsVisible} timeout="auto" unmountOnExit>
        <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            aria-label="Results tabs"
          >
            <Tab label={t("models:label.liveMetrics")} />
            <Tab
              label={
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <span>{t("models:label.explainability")}</span>
                  {isFinished && (
                    <Chip
                      label={globalExplainers.length + localExplainers.length}
                      size="small"
                      color="primary"
                    />
                  )}
                </Box>
              }
              disabled={!isFinished}
            />
            <Tab
              label={
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <span>{t("models:label.predictions")}</span>
                  {isFinished && (
                    <Chip
                      label={predictions.length}
                      size="small"
                      color="primary"
                    />
                  )}
                </Box>
              }
              disabled={!isFinished}
            />
            <Tab
              label={t("models:label.hyperparameters")}
              disabled={!isFinished || optimizables === 0}
            />
          </Tabs>
        </Box>

        {activeTab === 0 && (
          <Box sx={{ py: 2 }}>
            <LiveMetricsChart run={run} />
          </Box>
        )}

        {activeTab === 1 && isFinished && (
          <Box sx={{ py: 2, width: "100%" }}>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>
                <TimestampWrapper
                  eventName={TIMESTAMP_KEYS.explainer.configureGlobal}
                >
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={() => setGlobalCreatorOpen(true)}
                    fullWidth
                  >
                    {t("models:button.createGlobalExplainer")}
                  </Button>
                </TimestampWrapper>
              </Grid>
              <Grid item xs={6}>
                <TimestampWrapper
                  eventName={TIMESTAMP_KEYS.explainer.configureLocal}
                >
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={() => setLocalCreatorOpen(true)}
                    fullWidth
                  >
                    {t("models:button.createLocalExplainer")}
                  </Button>
                </TimestampWrapper>
              </Grid>
            </Grid>

            <InlineExplainerCreator
              open={globalCreatorOpen}
              scope="global"
              explainerConfig={{
                runId: run.id,
                taskName: session?.task_name,
              }}
              onCreated={handleExplainerCreated}
              onCancel={() => setGlobalCreatorOpen(false)}
            />
            <InlineExplainerCreator
              open={localCreatorOpen}
              scope="local"
              explainerConfig={{
                runId: run.id,
                taskName: session?.task_name,
              }}
              onCreated={handleExplainerCreated}
              onCancel={() => setLocalCreatorOpen(false)}
            />

            <Stack spacing={2}>
              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 2,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: globalExpanded ? 2 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography variant="subtitle2" fontWeight="medium">
                      {t("models:label.globalExplainers")}
                    </Typography>
                    <Chip
                      label={globalExplainers.length}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => setGlobalExpanded((prev) => !prev)}
                  >
                    {globalExpanded ? (
                      <ExpandLessIcon fontSize="small" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" />
                    )}
                  </IconButton>
                </Box>
                <Collapse in={globalExpanded}>
                  {globalExplainers.length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      align="center"
                      sx={{ py: 3 }}
                    >
                      {t("models:label.noGlobalExplainersYet")}
                    </Typography>
                  ) : (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(680px, 1fr))",
                        gap: 2,
                      }}
                    >
                      {globalExplainers.map((explainer) => (
                        <ExplainersCard
                          key={explainer.id}
                          explainer={explainer}
                          scope="global"
                          onDelete={handleExplainerDeleted}
                          compact
                        />
                      ))}
                    </Box>
                  )}
                </Collapse>
              </Box>

              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 2,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: localExpanded ? 2 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography variant="subtitle2" fontWeight="medium">
                      {t("models:label.localExplainers")}
                    </Typography>
                    <Chip
                      label={localExplainers.length}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => setLocalExpanded((prev) => !prev)}
                  >
                    {localExpanded ? (
                      <ExpandLessIcon fontSize="small" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" />
                    )}
                  </IconButton>
                </Box>
                <Collapse in={localExpanded}>
                  {localExplainers.length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      align="center"
                      sx={{ py: 3 }}
                    >
                      {t("models:label.noLocalExplainersYet")}
                    </Typography>
                  ) : (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(680px, 1fr))",
                        gap: 2,
                      }}
                    >
                      {localExplainers.map((explainer) => (
                        <ExplainersCard
                          key={explainer.id}
                          explainer={explainer}
                          scope="local"
                          onDelete={handleExplainerDeleted}
                          compact
                        />
                      ))}
                    </Box>
                  )}
                </Collapse>
              </Box>
            </Stack>
          </Box>
        )}

        {activeTab === 2 && isFinished && (
          <Box sx={{ py: 2, width: "100%" }}>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<TrendingUpIcon />}
                  onClick={() => setShowDatasetPanel(true)}
                  fullWidth
                >
                  {t("models:button.newDatasetPrediction")}
                </Button>
              </Grid>
              <Grid item xs={6}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<TrendingUpIcon />}
                  onClick={() => setShowManualPanel(true)}
                  fullWidth
                >
                  {t("models:button.newManualPrediction")}
                </Button>
              </Grid>
            </Grid>

            <Dialog
              open={showDatasetPanel}
              onClose={() => setShowDatasetPanel(false)}
              maxWidth="sm"
              fullWidth
              PaperProps={{ sx: { minHeight: "400px" } }}
            >
              <DialogTitle sx={{ bgcolor: "background.paper" }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Typography variant="h6" component="span">
                    {t("models:button.newDatasetPrediction")}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => setShowDatasetPanel(false)}
                    sx={{ color: "text.secondary" }}
                  >
                    <CloseIcon />
                  </IconButton>
                </Box>
              </DialogTitle>
              <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
                <DatasetPredictionPanel
                  run={run}
                  session={session}
                  onSaved={(prediction) => {
                    handlePredictionCreated(prediction);
                    setShowDatasetPanel(false);
                  }}
                  onClose={() => setShowDatasetPanel(false)}
                />
              </DialogContent>
            </Dialog>

            <Dialog
              open={showManualPanel}
              onClose={() => setShowManualPanel(false)}
              maxWidth="md"
              fullWidth
              PaperProps={{ sx: { minHeight: "500px" } }}
            >
              <DialogTitle sx={{ bgcolor: "background.paper" }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Typography variant="h6" component="span">
                    {t("models:button.newManualPrediction")}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => setShowManualPanel(false)}
                    sx={{ color: "text.secondary" }}
                  >
                    <CloseIcon />
                  </IconButton>
                </Box>
              </DialogTitle>
              <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
                <ManualPredictionPanel
                  run={run}
                  session={session}
                  onSaved={(prediction) => {
                    handlePredictionCreated(prediction);
                    setShowManualPanel(false);
                  }}
                  onClose={() => setShowManualPanel(false)}
                />
              </DialogContent>
            </Dialog>

            <Stack spacing={2}>
              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 2,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: datasetExpanded ? 2 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography variant="subtitle2" fontWeight="medium">
                      {t("models:label.datasetPredictions")}
                    </Typography>
                    <Chip
                      label={predictions.filter((p) => p.dataset_id).length}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => setDatasetExpanded((prev) => !prev)}
                  >
                    {datasetExpanded ? (
                      <ExpandLessIcon fontSize="small" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" />
                    )}
                  </IconButton>
                </Box>
                <Collapse in={datasetExpanded}>
                  {predictions.filter((p) => p.dataset_id).length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      align="center"
                      sx={{ py: 3 }}
                    >
                      {t("models:label.noDatasetPredictionsYet")}
                    </Typography>
                  ) : (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(680px, 1fr))",
                        gap: 2,
                      }}
                    >
                      {predictions
                        .filter((p) => p.dataset_id)
                        .map((prediction) => (
                          <PredictionCard
                            key={prediction.id}
                            prediction={prediction}
                            onDelete={handlePredictionDeleted}
                            onUpdate={fetchOperations}
                          />
                        ))}
                    </Box>
                  )}
                </Collapse>
              </Box>

              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 2,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: manualExpanded ? 2 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography variant="subtitle2" fontWeight="medium">
                      {t("models:label.manualPredictions")}
                    </Typography>
                    <Chip
                      label={predictions.filter((p) => !p.dataset_id).length}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => setManualExpanded((prev) => !prev)}
                  >
                    {manualExpanded ? (
                      <ExpandLessIcon fontSize="small" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" />
                    )}
                  </IconButton>
                </Box>
                <Collapse in={manualExpanded}>
                  {predictions.filter((p) => !p.dataset_id).length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      align="center"
                      sx={{ py: 3 }}
                    >
                      {t("models:label.noManualPredictionsYet")}
                    </Typography>
                  ) : (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(680px, 1fr))",
                        gap: 2,
                      }}
                    >
                      {predictions
                        .filter((p) => !p.dataset_id)
                        .map((prediction) => (
                          <PredictionCard
                            key={prediction.id}
                            prediction={prediction}
                            onDelete={handlePredictionDeleted}
                            onUpdate={fetchOperations}
                          />
                        ))}
                    </Box>
                  )}
                </Collapse>
              </Box>
            </Stack>
          </Box>
        )}

        {activeTab === 3 && isFinished && optimizables > 0 && (
          <Box sx={{ py: 2 }}>
            <HyperparameterPlots run={run} />
          </Box>
        )}
      </Collapse>
    </Box>
  );
}

RunResults.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string,
    model_name: PropTypes.string,
    status: PropTypes.number,
    experiment_id: PropTypes.number,
    parameters: PropTypes.object,
    model_session_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    test_metrics: PropTypes.object,
  }).isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onRefresh: PropTypes.func,
  explainerRefreshTrigger: PropTypes.number,
};
