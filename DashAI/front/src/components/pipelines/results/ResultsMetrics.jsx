import React, { useState } from "react";
import PropTypes from "prop-types";
import { Grid, Typography, Tooltip } from "@mui/material";

import ResultsTabMetricsToggle from "../../../pages/results/components/ResultsTabMetricsToggle";

function PipelineResultsMetrics({ metricsData = {} }) {
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
          Object.entries(currentMetrics).map(([metricName, metricData]) => {
            // Handle both old format (direct number) and new format (object with value and std_value)
            const value = metricData?.value ?? metricData;
            const stdValue = metricData?.std_value;

            const formattedValue =
              typeof value === "number" ? value.toFixed(4) : value;
            const formattedStd =
              stdValue !== null && stdValue !== undefined
                ? `±${Number(stdValue).toFixed(4)}`
                : null;

            const tooltipTitle = formattedStd
              ? `${formattedValue} ${formattedStd}`
              : formattedValue;

            return (
              <Tooltip
                key={metricName}
                title={tooltipTitle}
                placement="top"
                arrow
              >
                <Grid container>
                  <Grid size={{ xs: 1 }}>
                    <Typography variant="body1">{metricName}</Typography>
                  </Grid>
                  <Grid size={{ xs: 1 }}>
                    <Grid container direction="column" alignItems="flex-end">
                      <Typography variant="body1" align="right">
                        {formattedValue}
                      </Typography>
                      {formattedStd && (
                        <Typography variant="caption" color="text.secondary">
                          {formattedStd}
                        </Typography>
                      )}
                    </Grid>
                  </Grid>
                </Grid>
              </Tooltip>
            );
          })
        )}
      </Grid>
    </Grid>
  );
}

export default PipelineResultsMetrics;
