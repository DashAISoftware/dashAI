import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tabs,
  Tab,
  Paper,
  Button,
  CircularProgress,
} from "@mui/material";
import { ExpandMore, ArrowBackIosNew } from "@mui/icons-material";
import { getPipelineById } from "../../../api/pipeline";
import PipelineResultsMetrics from "./ResultsMetrics";
import PipelineResultsGraphs from "./ResultsGraphs";
import PipelineResultsPrediction from "./ResultsPrediction";
import ResultsTabParameters from "../../../pages/results/components/ResultsTabParameters";
import ResultsExploration from "./ResultsExploration";

const POLL_INTERVAL_MS = 3000;

function PipelineResults({ pipelineId, onClose }) {
  const [results, setResults] = useState(null);
  const [trainTab, setTrainTab] = useState(0);
  const [polling, setPolling] = useState(false);
  const pollingRef = useRef(null);

  /** Returns true when the pipeline has at least one result section populated. */
  const hasAnyResult = useCallback((data) => {
    if (!data) return false;
    const hasExpl =
      data.exploration && data.exploration !== "No exploration data";
    const hasTr = data.train && Object.keys(data.train).length > 0;
    const hasPred = data.prediction && data.prediction !== "No prediction data";
    return hasExpl || hasTr || hasPred;
  }, []);

  useEffect(() => {
    let cancelled = false;

    const fetchResults = async () => {
      try {
        const response = await getPipelineById(pipelineId);
        if (cancelled) return;
        setResults(response);

        // If results are not yet available, start polling
        if (!hasAnyResult(response)) {
          setPolling(true);
          // Clear any previous interval before setting a new one
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = setInterval(async () => {
            try {
              const updated = await getPipelineById(pipelineId);
              if (cancelled) return;
              setResults(updated);
              if (hasAnyResult(updated)) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
                setPolling(false);
              }
            } catch (err) {
              console.error("Error polling pipeline results:", err);
            }
          }, POLL_INTERVAL_MS);
        }
      } catch (error) {
        console.error("Error fetching results:", error);
      }
    };

    if (pipelineId) {
      fetchResults();
    }

    return () => {
      cancelled = true;
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [pipelineId, hasAnyResult]);

  const handleTabChange = (event, newValue) => {
    setTrainTab(newValue);
  };

  if (!results) {
    return <Typography>Loading results...</Typography>;
  }

  const hasExploration =
    results.exploration && results.exploration !== "No exploration data";
  const hasTrain = results.train && Object.keys(results.train).length > 0;
  const hasPrediction =
    results.prediction && results.prediction !== "No prediction data";

  const paramData = {
    parameters:
      results.train && results.train.parameters
        ? results.train.parameters
        : null,
  };

  if (!hasExploration && !hasTrain && !hasPrediction) {
    return (
      <Box sx={{ p: 2 }}>
        {onClose && (
          <Button startIcon={<ArrowBackIosNew />} onClick={onClose}>
            Volver
          </Button>
        )}
        {polling ? (
          <Box display="flex" alignItems="center" gap={2} mt={2}>
            <CircularProgress size={24} />
            <Typography>
              Pipeline is running. Results will appear automatically…
            </Typography>
          </Box>
        ) : (
          <Typography>No results available</Typography>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {hasExploration && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Exploration</Typography>
          </AccordionSummary>
          <AccordionDetails
            sx={{
              borderTop: "1px solid #383838",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <Box mx={10} my={2}>
              <ResultsExploration pipelineId={pipelineId} />
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasTrain && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Train</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2}>
              <Paper sx={{ width: "100%" }}>
                <Tabs
                  value={trainTab}
                  onChange={handleTabChange}
                  variant="scrollable"
                >
                  <Tab label="Info" />
                  <Tab label="Parameters" />
                  <Tab label="Metrics" />
                  <Tab label="Graphs" />
                </Tabs>
                <Box sx={{ p: 3 }}>
                  {trainTab === 0 && (
                    <Box>
                      <Typography variant="subtitle1">Model Name</Typography>
                      <Typography variant="p" sx={{ color: "gray" }}>
                        {results.train.info ?? "-"}
                      </Typography>
                    </Box>
                  )}
                  {trainTab === 1 && (
                    <Box>
                      <ResultsTabParameters runData={paramData} />
                    </Box>
                  )}
                  {trainTab === 2 && (
                    <Box>
                      <PipelineResultsMetrics
                        metricsData={results.train.metrics}
                      />
                    </Box>
                  )}
                  {trainTab === 3 && (
                    <Box>
                      <PipelineResultsGraphs metrics={results.train.metrics} />
                    </Box>
                  )}
                </Box>
              </Paper>
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasPrediction && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="h6">Prediction</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2}>
              <PipelineResultsPrediction prediction={results.prediction} />
            </Box>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
}

export default PipelineResults;
