import PropTypes from "prop-types";
import React, { useMemo } from "react";
import { Alert, AlertTitle } from "@mui/material";

import ResultsGraphs from "../../../pages/results/components/ResultsGraphs";

function normalizeSplitMetrics(splitMetrics) {
  return splitMetrics && typeof splitMetrics === "object" ? splitMetrics : {};
}

function PipelineResultsGraphs({ metrics }) {
  const trainMetrics = normalizeSplitMetrics(metrics?.train);
  const validationMetrics = normalizeSplitMetrics(metrics?.validation);
  const testMetrics = normalizeSplitMetrics(metrics?.test);

  const hasAnyMetrics =
    Object.keys(trainMetrics).length > 0 ||
    Object.keys(validationMetrics).length > 0 ||
    Object.keys(testMetrics).length > 0;

  const syntheticRuns = useMemo(
    () => [
      {
        status: 3,
        train_metrics: trainMetrics,
        validation_metrics: validationMetrics,
        test_metrics: testMetrics,
      },
    ],
    [trainMetrics, validationMetrics, testMetrics],
  );

  if (!hasAnyMetrics) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        <AlertTitle>No metric data available</AlertTitle>
        Please provide valid metrics to render the graphs.
      </Alert>
    );
  }

  return <ResultsGraphs runs={syntheticRuns} />;
}

PipelineResultsGraphs.propTypes = {
  metrics: PropTypes.shape({
    train: PropTypes.object,
    validation: PropTypes.object,
    test: PropTypes.object,
  }),
};

PipelineResultsGraphs.defaultProps = {
  metrics: {},
};

export default PipelineResultsGraphs;
