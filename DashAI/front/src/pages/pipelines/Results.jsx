import React, { useEffect, useState } from "react";
import { Box, Typography, Accordion, AccordionSummary, AccordionDetails } from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import { getPipelineById } from "../../api/pipeline";

function PipelineResults({ pipelineId }) {
  const [results, setResults] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await getPipelineById(pipelineId);
        console.log("Pipeline results:", response);
        setResults(response);
      } catch (error) {
        console.error("Error fetching results:", error);
      }
    };

    if (pipelineId) {
      fetchResults();
    }
  }, [pipelineId]);

  if (!results) {
    return <Typography>Loading results...</Typography>;
  }

  const renderValue = (value) => {
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return value;
  };

  const hasExploration = results.exploration && results.exploration !== "No exploration data";
  const hasTrain = results.train && Object.keys(results.train).length > 0;
  const hasPrediction = results.prediction && results.prediction !== "No prediction data";

  return (
    <Box sx={{ p: 2 }}>

      {hasExploration && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Exploration</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography>{renderValue(results.exploration)}</Typography>
          </AccordionDetails>
        </Accordion>
      )}

      {hasTrain && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Train</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {Object.entries(results.train).map(([key, value]) => (
              <Typography key={key}>
                {key}: {renderValue(value)}
              </Typography>
            ))}
          </AccordionDetails>
        </Accordion>
      )}

      {hasPrediction && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Prediction</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography>{renderValue(results.prediction)}</Typography>
          </AccordionDetails>
        </Accordion>
      )}

      {!hasExploration && !hasTrain && !hasPrediction && (
        <Typography>No results available</Typography>
      )}
    </Box>
  );
}

export default PipelineResults;