import React, { useState, useEffect, useCallback, useRef } from "react";
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
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";
import { renderParamValue } from "./ModelParamBlock";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Add as AddIcon,
  TrendingUp as TrendingUpIcon,
  Close as CloseIcon,
} from "@mui/icons-material";
import ExplainersCard from "../explainers/ExplainersCard";
import PredictionCard from "./PredictionCard";
import { LoadingButton } from "@mui/lab";
import InlineExplainerCreator from "../explainers/InlineExplainerCreator";
import DatasetPredictionPanel from "./DatasetPredictionPanel";
import ManualPredictionPanel from "./ManualPredictionPanel";
import LiveMetricsChart from "./LiveMetricsChart";
import HyperparameterPlots from "./HyperparameterPlots";
import { getExplainers } from "../../api/explainer";
import { getPredictions } from "../../api/predict";
import { getModelSessionById } from "../../api/modelSession";
import { getDatasetSample } from "../../api/datasets";
import { checkHowManyOptimazers } from "../../utils/schema";
import { useTranslation } from "react-i18next";
import TimestampWrapper from "../shared/TimestampWrapper";
import { TIMESTAMP_KEYS } from "../../constants/timestamp";

export default function RunResults({
  run,
  model,
  session,
  onRefresh,
  explainerRefreshTrigger,
  resultsVisible: controlledVisible = undefined,
  setResultsVisible: setControlledVisible = undefined,
  autoExpand = false,
}) {
  const isControlled = controlledVisible !== undefined;

  const [globalExplainers, setGlobalExplainers] = useState([]);
  const [localExplainers, setLocalExplainers] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [internalVisible, setInternalVisible] = useState(() => {
    if (run.status === 0) return false;
    const saved = localStorage.getItem(`run-${run.id}-results-visible`);
    return saved ? JSON.parse(saved) : false;
  });
  const resultsVisible = isControlled ? controlledVisible : internalVisible;
  const setResultsVisible = isControlled
    ? setControlledVisible
    : setInternalVisible;

  const [paramsExpanded, setParamsExpanded] = useState(false);

  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem(`run-${run.id}-active-tab`);
    if (saved !== null) {
      const savedTab = JSON.parse(saved);
      // Tabs 1+ (Explainability, Predictions, Hyperparameters) require a finished run
      if (savedTab > 0 && run.status !== 3) return 0;
      return savedTab;
    }
    return 0;
  });

  const [trainingDatasetSample, setTrainingDatasetSample] = useState(null);
  const [outputColumn, setOutputColumn] = useState(null);

  const [globalCreatorOpen, setGlobalCreatorOpen] = useState(false);
  const [localCreatorOpen, setLocalCreatorOpen] = useState(false);
  const [globalExpanded, setGlobalExpanded] = useState(true);
  const [localExpanded, setLocalExpanded] = useState(true);
  const [datasetExpanded, setDatasetExpanded] = useState(true);
  const [manualExpanded, setManualExpanded] = useState(true);
  const [showDatasetPanel, setShowDatasetPanel] = useState(false);
  const datasetRunRef = useRef(null);
  const [datasetRunState, setDatasetRunState] = useState({
    canRun: false,
    isSubmitting: false,
  });
  const [showManualPanel, setShowManualPanel] = useState(false);
  const manualSaveRef = useRef(null);
  const [manualSaveState, setManualSaveState] = useState({
    canSave: false,
    isSaving: false,
  });

  // Map a parameter key to its display name using the matching model's schema
  // (the model comes from the right side bar list, so no extra backend fetch).
  const paramProperties = model?.schema?.properties ?? {};
  const getParamLabel = (key) => paramProperties[key]?.title ?? key;

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

  useEffect(() => {
    const sessionId = run.model_session_id || session?.id;
    if (!sessionId) return;
    let cancelled = false;
    getModelSessionById(sessionId)
      .then((sessionData) => {
        if (cancelled) return null;
        setOutputColumn(sessionData.output_columns?.[0] ?? null);
        return getDatasetSample(sessionData.dataset_id);
      })
      .then((sample) => {
        if (!cancelled && sample) setTrainingDatasetSample(sample);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [run.model_session_id, session?.id]);

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
    if (isRunning && autoExpand) {
      setResultsVisible(true);
      setActiveTab(0); // Live Metrics tab
    }
  }, [isRunning, autoExpand]);

  useEffect(() => {
    if (isControlled) return;
    localStorage.setItem(
      `run-${run.id}-results-visible`,
      JSON.stringify(resultsVisible),
    );
  }, [resultsVisible, run.id, isControlled]);

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

  const hasParams =
    (run.parameters && Object.keys(run.parameters).length > 0) ||
    (run.optimizer_name && run.goal_metric);

  return (
    <Box id={`run-results-${run.id}`}>
      {hasParams && (
        <Box sx={{ mb: 4 }}>
          <Button
            size="small"
            onClick={() => setParamsExpanded(!paramsExpanded)}
            endIcon={paramsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            sx={{ textTransform: "none" }}
          >
            {t("common:modelParameters")}
          </Button>
          <Collapse in={paramsExpanded} timeout="auto" unmountOnExit>
            <Box sx={{ mt: 2 }}>
              {run.parameters && Object.keys(run.parameters).length > 0 && (
                <Box sx={{ mb: 4 }}>
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>{t("common:parameter")}</TableCell>
                          <TableCell>{t("common:value")}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(run.parameters).map(([key, value]) => (
                          <TableRow key={key}>
                            <TableCell>{getParamLabel(key)}</TableCell>
                            <TableCell>{renderParamValue(value)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
              {run.optimizer_name && run.goal_metric && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    {t("common:optimizer")}: {run.optimizer_name}
                  </Typography>
                  {run.optimizer_parameters &&
                    Object.keys(run.optimizer_parameters).length > 0 && (
                      <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>{t("common:parameter")}</TableCell>
                              <TableCell>{t("common:value")}</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {Object.entries(run.optimizer_parameters).map(
                              ([key, value]) => (
                                <TableRow key={key}>
                                  <TableCell>{key}</TableCell>
                                  <TableCell>
                                    {renderParamValue(value)}
                                  </TableCell>
                                </TableRow>
                              ),
                            )}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 2 }}
                  >
                    {t("models:label.goalMetric")}:{" "}
                    <strong>{run.goal_metric}</strong>
                  </Typography>
                </Box>
              )}
            </Box>
          </Collapse>
        </Box>
      )}

      <Collapse in={resultsVisible} timeout="auto" unmountOnExit>
        <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 4 }}>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            aria-label="Results tabs"
          >
            <Tab label={t("models:label.liveMetrics")} />
            <Tab
              label={
                <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
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
                <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
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
          <Box sx={{ py: 4 }}>
            <LiveMetricsChart run={run} />
          </Box>
        )}

        {activeTab === 1 && isFinished && (
          <Box sx={{ py: 4, width: "100%" }}>
            <Grid container spacing={4} sx={{ mb: 4 }}>
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

            <Stack spacing={4}>
              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 4,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: globalExpanded ? 4 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
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
                      sx={{ py: 6 }}
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
                  p: 4,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: localExpanded ? 4 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
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
                      sx={{ py: 6 }}
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
          <Box sx={{ py: 4, width: "100%" }}>
            <Grid container spacing={4} sx={{ mb: 4 }}>
              <Grid item xs={6}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<TrendingUpIcon />}
                  onClick={() => {
                    setDatasetRunState({ canRun: false, isSubmitting: false });
                    setShowDatasetPanel(true);
                  }}
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
                  onClick={() => {
                    setManualSaveState({ canSave: false, isSaving: false });
                    setShowManualPanel(true);
                  }}
                  fullWidth
                >
                  {t("models:button.newManualPrediction")}
                </Button>
              </Grid>
            </Grid>

            <Dialog
              open={showDatasetPanel}
              onClose={() => setShowDatasetPanel(false)}
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
                  runRef={datasetRunRef}
                  onStateChange={setDatasetRunState}
                />
              </DialogContent>
              <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
                <Button
                  variant="outlined"
                  onClick={() => setShowDatasetPanel(false)}
                  disabled={datasetRunState.isSubmitting}
                >
                  {t("common:cancel")}
                </Button>
                <LoadingButton
                  variant="contained"
                  color="primary"
                  disabled={!datasetRunState.canRun}
                  loading={datasetRunState.isSubmitting}
                  onClick={() => datasetRunRef.current?.()}
                >
                  {t("prediction:button.runPrediction")}
                </LoadingButton>
              </DialogActions>
            </Dialog>

            <Dialog
              open={showManualPanel}
              onClose={() => setShowManualPanel(false)}
              maxWidth="lg"
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
                  saveRef={manualSaveRef}
                  onStateChange={setManualSaveState}
                />
              </DialogContent>
              <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
                <Button
                  variant="outlined"
                  onClick={() => setShowManualPanel(false)}
                  disabled={manualSaveState.isSaving}
                >
                  {t("common:cancel")}
                </Button>
                <LoadingButton
                  variant="contained"
                  color="primary"
                  disabled={!manualSaveState.canSave}
                  loading={manualSaveState.isSaving}
                  onClick={() => manualSaveRef.current?.()}
                >
                  {t("prediction:button.saveResults")}
                </LoadingButton>
              </DialogActions>
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
                            targetColumn={outputColumn}
                            datasetSample={trainingDatasetSample}
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
                            targetColumn={outputColumn}
                            datasetSample={trainingDatasetSample}
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
          <Box sx={{ py: 4 }}>
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
  model: PropTypes.shape({
    name: PropTypes.string,
    display_name: PropTypes.string,
    schema: PropTypes.object,
  }),
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onRefresh: PropTypes.func,
  explainerRefreshTrigger: PropTypes.number,
  resultsVisible: PropTypes.bool,
  setResultsVisible: PropTypes.func,
  autoExpand: PropTypes.bool,
};
