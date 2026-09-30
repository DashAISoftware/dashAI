import React, { useState } from "react";
import PropTypes from "prop-types";
import { Grid, Typography } from "@mui/material";

import ResultsTabMetricsToggle from "../../../pages/results/components/ResultsTabMetricsToggle";

function PipelineResultsMetrics({ metricsData = {} }) {
  const [displaySet, setDisplaySet] = useState("test_metrics");

  // The default parameter only covers `undefined`; guard against an explicit
  // `null` so the component never crashes if it is ever rendered without data.
  const safeMetricsData = metricsData || {};

  const displaySetMap = {
    train_metrics: "train",
    test_metrics: "test",
    validation_metrics: "validation",
  };

  const currentKey = displaySetMap[displaySet];
  const currentMetrics = safeMetricsData[currentKey] || {};

  const hasTrainData = !!safeMetricsData.train;
  const hasTestData = !!safeMetricsData.test;
  const hasValidationData = !!safeMetricsData.validation;

  return (
    <Grid container direction="column" rowSpacing={4}>
      <ResultsTabMetricsToggle
        displaySet={displaySet}
        setDisplaySet={setDisplaySet}
        hasTrainData={hasTrainData}
        hasTestData={hasTestData}
        hasValidationData={hasValidationData}
      />

      <Grid container direction="column" spacing={2}>
        {Object.keys(currentMetrics).length === 0 ? (
          <Typography variant="body1">
            No metrics available for {displaySet.replace("_metrics", "")} set.
          </Typography>
        ) : (
          Object.entries(currentMetrics).map(([metricName, value]) => (
            <Grid container key={metricName} columnSpacing={3}>
              <Grid size={{ xs: 3 }}>
                <Typography variant="body1" fontWeight="bold">
                  {metricName}
                </Typography>
              </Grid>
              <Grid size={{ xs: 2 }}>
                <Typography variant="body1">
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
