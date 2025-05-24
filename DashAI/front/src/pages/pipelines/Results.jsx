import React, { useEffect, useState } from "react";
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
} from "@mui/material";
import { ExpandMore, ArrowBackIosNew } from "@mui/icons-material";
import { getPipelineById } from "../../api/pipeline";
import PipelineResultsMetrics from "./ResultsMetrics";
import PipelineResultsGraphs from "./ResultsGraphs";
import PipelineResultsPrediction from "./ResultsPrediction";
import ResultsTabParameters from "../results/components/ResultsTabParameters";

function PipelineResults({ pipelineId, onClose }) {
  const [results, setResults] = useState(null);
  const [trainTab, setTrainTab] = useState(0);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await getPipelineById(pipelineId);
        setResults(response);
      } catch (error) {
        console.error("Error fetching results:", error);
      }
    };

    if (pipelineId) {
      fetchResults();
    }
  }, [pipelineId]);

  const handleTabChange = (event, newValue) => {
    setTrainTab(newValue);
  };

  if (!results) {
    return <Typography>Loading results...</Typography>;
  }

  const renderValue = (value) => {
    if (typeof value === "object" && value !== null) {
      return <pre>{JSON.stringify(value, null, 2)}</pre>;
    }
    return value;
  };

  const hasExploration =
    results.exploration && results.exploration !== "No exploration data";
  const hasTrain = results.train && Object.keys(results.train).length > 0;
  const hasPrediction =
    results.prediction && results.prediction !== "No prediction data";

  const paramData = {
    parameters:
      results.train && results.train.parameters ? results.train.parameters : null,
  };

  if (!hasExploration && !hasTrain && !hasPrediction) {
    return (
      <Box sx={{ p: 2 }}>
        {onClose && (
          <Button startIcon={<ArrowBackIosNew />} onClick={onClose}>
            Volver
          </Button>
        )}
        <Typography>No results available</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {onClose && (
        <Button startIcon={<ArrowBackIosNew />} onClick={onClose}>
          Volver
        </Button>
      )}

      {hasExploration && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Exploration</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2}>
              {renderValue(results.exploration)}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {hasTrain && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Train</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ borderTop: "1px solid #383838" }}>
            <Box mx={10} my={2}>
              <Paper sx={{ width: "100%" }}>
                <Tabs value={trainTab} onChange={handleTabChange} variant="scrollable">
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
                      <PipelineResultsMetrics metricsData={results.train.metrics} />
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
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Prediction</Typography>
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
