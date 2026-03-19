import React, { useState } from "react";
import PropTypes from "prop-types";
import { Grid, Typography } from "@mui/material";

import ResultsTabMetricsToggle from "../../../pages/results/components/ResultsTabMetricsToggle";

const EMPTY_METRICS_DATA = {};

function PipelineResultsMetrics({ metricsData = EMPTY_METRICS_DATA }) {
  const [displaySet, setDisplaySet] = useState("test_metrics");

  const displaySetMap = {
    train_metrics: "train",
    test_metrics: "test",
    validation_metrics: "validation",
  };

  const currentKey = displaySetMap[displaySet];
  const currentMetrics = metricsData[currentKey] || {};

  const hasTrainData = !!metricsData.train;
  const hasTestData = !!metricsData.test;
  const hasValidationData = !!metricsData.validation;

  return (
    <Grid container direction="column" rowSpacing={2}>
      <ResultsTabMetricsToggle
        displaySet={displaySet}
        setDisplaySet={setDisplaySet}
        hasTrainData={hasTrainData}
        hasTestData={hasTestData}
        hasValidationData={hasValidationData}
      />

      <Grid container direction="column" spacing={1}>
        {Object.keys(currentMetrics).length === 0 ? (
          <Typography variant="body1">
            No metrics available for {displaySet.replace("_metrics", "")} set.
          </Typography>
        ) : (
          Object.entries(currentMetrics).map(([metricName, value]) => (
            <Grid container key={metricName}>
              <Grid size={{ xs: 1 }}>
                <Typography variant="body1">{metricName}</Typography>
              </Grid>
              <Grid size={{ xs: 1 }}>
                <Typography variant="body1" align="right">
                  {typeof value === "number" ? value.toFixed(4) : value}
                </Typography>
              </Grid>
            </Grid>
          ))
        )}
      </Grid>
    </Grid>
  );
}

export default PipelineResultsMetrics;
