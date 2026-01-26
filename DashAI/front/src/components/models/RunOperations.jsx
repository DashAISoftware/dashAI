import React, { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Button,
  Chip,
  Stack,
  CircularProgress,
  Collapse,
  Tabs,
  Tab,
  Grid,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Add as AddIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import ExplainersCard from "../explainers/ExplanainersCard";
import PredictionCard from "./PredictionCard";
import NewGlobalExplainerModal from "../explainers/NewGlobalExplainerModal";
import NewLocalExplainerModal from "../explainers/NewLocalExplainerModal";
import PredictionCreationDialog from "./PredictionCreationDialog";
import { getExplainers } from "../../api/explainer";
import { getPredictions } from "../../api/predict";
import { useSnackbar } from "notistack";

/**
 * RunOperations component - Shows explainers and predictions for a finished run
 * Displays as expandable sections within a RunCard
 */
export default function RunOperations({
  run,
  session,
  onRefresh,
  explainerRefreshTrigger,
}) {
  const [globalExplainers, setGlobalExplainers] = useState([]);
  const [localExplainers, setLocalExplainers] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [operationsVisible, setOperationsVisible] = useState(() => {
    const saved = localStorage.getItem(`run-${run.id}-operations-visible`);
    return saved !== null ? JSON.parse(saved) : false;
  });
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem(`run-${run.id}-active-tab`);
    return saved !== null ? JSON.parse(saved) : 0;
  });

  const [globalDialogOpen, setGlobalDialogOpen] = useState(false);
  const [localDialogOpen, setLocalDialogOpen] = useState(false);
  const [datasetPredictionDialogOpen, setDatasetPredictionDialogOpen] =
    useState(false);
  const [manualPredictionDialogOpen, setManualPredictionDialogOpen] =
    useState(false);

  const fetchOperations = useCallback(async () => {
    if (!run || !run.id) return;

    setLoading(true);
    try {
      const [globalExpls, localExpls, preds] = await Promise.all([
        getExplainers(run.id, "global").catch(() => []),
        getExplainers(run.id, "local").catch(() => []),
        getPredictions(run.id).catch(() => []),
      ]);

      setGlobalExplainers(globalExpls);
      setLocalExplainers(localExpls);
      setPredictions(preds);
    } catch (error) {
      console.error("Error fetching operations:", error);
    } finally {
      setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    fetchOperations();
  }, [fetchOperations, explainerRefreshTrigger]);

  // Listen for prediction dialog open event
  useEffect(() => {
    const handleOpenDialog = (event) => {
      if (event.detail.runId === run.id) {
        setDatasetPredictionDialogOpen(true);
      }
    };
    window.addEventListener("openPredictionDialog", handleOpenDialog);
    return () =>
      window.removeEventListener("openPredictionDialog", handleOpenDialog);
  }, [run.id]);

  // Persist operationsVisible state
  useEffect(() => {
    localStorage.setItem(
      `run-${run.id}-operations-visible`,
      JSON.stringify(operationsVisible),
    );
  }, [operationsVisible, run.id]);

  // Persist activeTab state
  useEffect(() => {
    localStorage.setItem(`run-${run.id}-active-tab`, JSON.stringify(activeTab));
  }, [activeTab, run.id]);

  const handleExplainerCreated = () => {
    fetchOperations();
    if (onRefresh) onRefresh();
  };

  const handlePredictionCreated = (prediction) => {
    if (prediction) {
      setPredictions((prev) => [prediction, ...prev]);
    }
    fetchOperations();
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

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <Box id={`run-operations-${run.id}`}>
      {/* Header with Show/Hide button */}
      <Box sx={{ mb: 2 }}>
        <Button
          size="small"
          onClick={() => setOperationsVisible(!operationsVisible)}
          endIcon={operationsVisible ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          sx={{ textTransform: "none" }}
        >
          {operationsVisible ? "Hide Operations" : "Show Operations"}
          <Chip label={totalOperations} size="small" sx={{ ml: 1 }} />
        </Button>
      </Box>

      <Collapse in={operationsVisible} timeout="auto" unmountOnExit>
        {/* Tabs for Explainability and Predictions */}
        <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            aria-label="Operations tabs"
          >
            <Tab
              label={
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <span>Explainability</span>
                  <Chip
                    label={globalExplainers.length + localExplainers.length}
                    size="small"
                    color="primary"
                  />
                </Box>
              }
            />
            <Tab
              label={
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <span>Predictions</span>
                  <Chip
                    label={predictions.length}
                    size="small"
                    color="primary"
                  />
                </Box>
              }
            />
          </Tabs>
        </Box>

        {/* Tab Panel 0: Explainability */}
        {activeTab === 0 && (
          <Box sx={{ py: 2 }}>
            <Grid container spacing={2}>
              {/* Global Explainers Column */}
              <Grid item xs={12} md={6}>
                <Box
                  sx={{
                    border: 1,
                    borderColor: "divider",
                    borderRadius: 1,
                    p: 2,
                    height: "100%",
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 2,
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="body1" fontWeight="medium">
                        Global Explainers
                      </Typography>
                      <Chip
                        label={globalExplainers.length}
                        size="small"
                        color="primary"
                      />
                    </Box>
                  </Box>
                  <Stack spacing={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={() => setGlobalDialogOpen(true)}
                      fullWidth
                    >
                      New Global Explainer
                    </Button>
                    {globalExplainers.length === 0 ? (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        align="center"
                        sx={{ py: 3 }}
                      >
                        No global explainers yet
                      </Typography>
                    ) : (
                      globalExplainers.map((explainer) => (
                        <ExplainersCard
                          key={explainer.id}
                          explainer={explainer}
                          scope="global"
                          onDelete={handleExplainerDeleted}
                          compact
                        />
                      ))
                    )}
                  </Stack>
                </Box>
              </Grid>

              {/* Local Explainers Column */}
              <Grid item xs={12} md={6}>
                <Box
                  sx={{
                    border: 1,
                    borderColor: "divider",
                    borderRadius: 1,
                    p: 2,
                    height: "100%",
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 2,
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="body1" fontWeight="medium">
                        Local Explainers
                      </Typography>
                      <Chip
                        label={localExplainers.length}
                        size="small"
                        color="primary"
                      />
                    </Box>
                  </Box>
                  <Stack spacing={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={() => setLocalDialogOpen(true)}
                      fullWidth
                    >
                      New Local Explainer
                    </Button>
                    {localExplainers.length === 0 ? (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        align="center"
                        sx={{ py: 3 }}
                      >
                        No local explainers yet
                      </Typography>
                    ) : (
                      localExplainers.map((explainer) => (
                        <ExplainersCard
                          key={explainer.id}
                          explainer={explainer}
                          scope="local"
                          onDelete={handleExplainerDeleted}
                          compact
                        />
                      ))
                    )}
                  </Stack>
                </Box>
              </Grid>
            </Grid>
          </Box>
        )}

        {/* Tab Panel 1: Predictions */}
        {activeTab === 1 && (
          <Box sx={{ py: 2 }}>
            <Grid container spacing={2}>
              {/* Dataset Predictions Column */}
              <Grid item xs={12} md={6}>
                <Box
                  sx={{
                    border: 1,
                    borderColor: "divider",
                    borderRadius: 1,
                    p: 2,
                    height: "100%",
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 2,
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="body1" fontWeight="medium">
                        Dataset Predictions
                      </Typography>
                      <Chip
                        label={predictions.filter((p) => p.dataset_id).length}
                        size="small"
                        color="primary"
                      />
                    </Box>
                  </Box>
                  <Stack spacing={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<TrendingUpIcon />}
                      onClick={() => setDatasetPredictionDialogOpen(true)}
                      fullWidth
                    >
                      New Dataset Prediction
                    </Button>
                    {predictions.filter((p) => p.dataset_id).length === 0 ? (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        align="center"
                        sx={{ py: 3 }}
                      >
                        No dataset predictions yet
                      </Typography>
                    ) : (
                      predictions
                        .filter((p) => p.dataset_id)
                        .map((prediction) => (
                          <PredictionCard
                            key={prediction.id}
                            prediction={prediction}
                            onDelete={handlePredictionDeleted}
                            onUpdate={fetchOperations}
                          />
                        ))
                    )}
                  </Stack>
                </Box>
              </Grid>

              {/* Manual Predictions Column */}
              <Grid item xs={12} md={6}>
                <Box
                  sx={{
                    border: 1,
                    borderColor: "divider",
                    borderRadius: 1,
                    p: 2,
                    height: "100%",
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 2,
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="body1" fontWeight="medium">
                        Manual Predictions
                      </Typography>
                      <Chip
                        label={predictions.filter((p) => !p.dataset_id).length}
                        size="small"
                        color="primary"
                      />
                    </Box>
                  </Box>
                  <Stack spacing={2}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<TrendingUpIcon />}
                      onClick={() => setManualPredictionDialogOpen(true)}
                      fullWidth
                    >
                      New Manual Prediction
                    </Button>
                    {predictions.filter((p) => !p.dataset_id).length === 0 ? (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        align="center"
                        sx={{ py: 3 }}
                      >
                        No manual predictions yet
                      </Typography>
                    ) : (
                      predictions
                        .filter((p) => !p.dataset_id)
                        .map((prediction) => (
                          <PredictionCard
                            key={prediction.id}
                            prediction={prediction}
                            onDelete={handlePredictionDeleted}
                            onUpdate={fetchOperations}
                          />
                        ))
                    )}
                  </Stack>
                </Box>
              </Grid>
            </Grid>
          </Box>
        )}
      </Collapse>

      {/* Dialogs */}
      <NewGlobalExplainerModal
        open={globalDialogOpen}
        setOpen={setGlobalDialogOpen}
        explainerConfig={{
          runId: run.id,
          taskName: session?.task_name,
        }}
        onExplainerCreated={handleExplainerCreated}
      />

      <NewLocalExplainerModal
        open={localDialogOpen}
        setOpen={setLocalDialogOpen}
        explainerConfig={{
          runId: run.id,
          sessionId: session?.id,
          taskName: session?.task_name,
        }}
        onExplainerCreated={handleExplainerCreated}
      />

      <PredictionCreationDialog
        open={datasetPredictionDialogOpen}
        onClose={() => setDatasetPredictionDialogOpen(false)}
        run={run}
        session={session}
        onPredictionCreated={handlePredictionCreated}
        defaultMode="dataset"
      />

      <PredictionCreationDialog
        open={manualPredictionDialogOpen}
        onClose={() => setManualPredictionDialogOpen(false)}
        run={run}
        session={session}
        onPredictionCreated={handlePredictionCreated}
        defaultMode="manual"
      />
    </Box>
  );
}

RunOperations.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string,
    model_name: PropTypes.string,
    status: PropTypes.number,
    experiment_id: PropTypes.number,
  }).isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onRefresh: PropTypes.func,
  explainerRefreshTrigger: PropTypes.number,
};
