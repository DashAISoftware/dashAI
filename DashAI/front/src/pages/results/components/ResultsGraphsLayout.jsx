import React from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";

import ResultsGraphsSelection from "./ResultsGraphsSelection";
import ResultsGraphsParameters from "./ResultsGraphsParameters";
import ResultsGraphsPlot from "./ResultsGraphsPlot";
import FoldMetricsChart from "../../../components/models/FoldMetricsChart";

function ResultsGraphsLayout({
  selectedChart,
  handleChangeChart,
  currentMetrics,
  selectedMetrics,
  handleToggleMetric,
  handleSelectAll,
  handleClearAll,
  chartData,
  expandedRunId = null,
  selectedSplit = "test",
  runs = [],
}) {
  // Get metrics from the expanded run
  const expandedRun = expandedRunId
    ? runs.find((r) => r.id === expandedRunId)
    : null;
  const metrics = expandedRun
    ? Object.keys(expandedRun[`${selectedSplit}_metrics`] || {}).map(
        (name) => ({ name, metadata: {} }),
      )
    : [];
  const isCrossValidation =
    runs[0]?.evaluation_strategy === "CrossValidationEvaluationStrategy";
  const isNestedCV =
    expandedRun?.nested !== null && expandedRun?.nested !== undefined;
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="stretch"
      width="100%"
      height="100%"
    >
      {/* Chart type selector */}
      <ResultsGraphsSelection
        selectedChart={selectedChart}
        handleChangeChart={handleChangeChart}
        isCv={isCrossValidation}
      />

      <Box display="flex" flex={1} width="100%">
        {/* Show FoldMetricsChart when selected */}
        {selectedChart === "fold_metrics" ? (
          <Box sx={{ width: "100%", p: 2, overflow: "auto" }}>
            {expandedRunId ? (
              <FoldMetricsChart
                runId={expandedRunId}
                metricSplit={selectedSplit}
                metrics={metrics}
                isNestedCV={isNestedCV}
              />
            ) : (
              <Box sx={{ p: 2, textAlign: "center", color: "text.secondary" }}>
                <Typography variant="body2">
                  Select a run from the table to view its cross-validation fold
                  metrics
                </Typography>
              </Box>
            )}
          </Box>
        ) : (
          <>
            {/* Metric filter sidebar */}
            <ResultsGraphsParameters
              currentMetrics={currentMetrics}
              selectedMetrics={selectedMetrics}
              handleToggleMetric={handleToggleMetric}
              handleSelectAll={handleSelectAll}
              handleClearAll={handleClearAll}
            />

            {/* Plotly chart area */}
            <ResultsGraphsPlot
              selectedChart={selectedChart}
              chartData={chartData}
            />
          </>
        )}
      </Box>
    </Box>
  );
}

ResultsGraphsLayout.propTypes = {
  selectedChart: PropTypes.string.isRequired,
  handleChangeChart: PropTypes.func.isRequired,
  currentMetrics: PropTypes.array.isRequired,
  selectedMetrics: PropTypes.array.isRequired,
  handleToggleMetric: PropTypes.func.isRequired,
  handleSelectAll: PropTypes.func.isRequired,
  handleClearAll: PropTypes.func.isRequired,
  chartData: PropTypes.object.isRequired,
  expandedRunId: PropTypes.number,
  selectedSplit: PropTypes.string,
  runs: PropTypes.array,
};

export default ResultsGraphsLayout;
