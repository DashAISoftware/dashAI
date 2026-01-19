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
  const [operationsVisible, setOperationsVisible] = useState(false);

  const [globalDialogOpen, setGlobalDialogOpen] = useState(false);
  const [localDialogOpen, setLocalDialogOpen] = useState(false);
  const [predictionDialogOpen, setPredictionDialogOpen] = useState(false);

  const [expandedSections, setExpandedSections] = useState({
    globalExplainers: false,
    localExplainers: false,
    predictions: false,
  });

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
        setPredictionDialogOpen(true);
      }
    };
    window.addEventListener("openPredictionDialog", handleOpenDialog);
    return () =>
      window.removeEventListener("openPredictionDialog", handleOpenDialog);
  }, [run.id]);

  const handleAccordionChange = (section) => (event, isExpanded) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: isExpanded,
    }));
  };

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
        {/* Global Explainers Section */}
        <Accordion
          expanded={expandedSections.globalExplainers}
          onChange={handleAccordionChange("globalExplainers")}
          sx={{ mb: 1 }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box
              sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}
            >
              <Typography variant="body2" fontWeight="medium">
                Global Explainers
              </Typography>
              <Chip
                label={globalExplainers.length}
                size="small"
                color="primary"
              />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
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
          </AccordionDetails>
        </Accordion>

        {/* Local Explainers Section */}
        <Accordion
          expanded={expandedSections.localExplainers}
          onChange={handleAccordionChange("localExplainers")}
          sx={{ mb: 1 }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box
              sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}
            >
              <Typography variant="body2" fontWeight="medium">
                Local Explainers
              </Typography>
              <Chip
                label={localExplainers.length}
                size="small"
                color="primary"
              />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
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
          </AccordionDetails>
        </Accordion>

        {/* Predictions Section */}
        <Accordion
          expanded={expandedSections.predictions}
          onChange={handleAccordionChange("predictions")}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box
              sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}
            >
              <Typography variant="body2" fontWeight="medium">
                Predictions
              </Typography>
              <Chip label={predictions.length} size="small" color="primary" />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <Button
                variant="outlined"
                size="small"
                startIcon={<TrendingUpIcon />}
                onClick={() => setPredictionDialogOpen(true)}
                fullWidth
              >
                New Prediction
              </Button>
              {predictions.length === 0 ? (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  align="center"
                >
                  No predictions yet
                </Typography>
              ) : (
                predictions.map((prediction) => (
                  <PredictionCard
                    key={prediction.id}
                    prediction={prediction}
                    onDelete={handlePredictionDeleted}
                    onUpdate={fetchOperations}
                  />
                ))
              )}
            </Stack>
          </AccordionDetails>
        </Accordion>
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
        open={predictionDialogOpen}
        onClose={() => setPredictionDialogOpen(false)}
        run={run}
        session={session}
        onPredictionCreated={handlePredictionCreated}
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
    model_session_id: PropTypes.number,
  }).isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onRefresh: PropTypes.func,
  explainerRefreshTrigger: PropTypes.number,
};
