import React from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";

import ResultsGraphsParameters from "./ResultsGraphsParameters";
import ResultsGraphsPlot from "./ResultsGraphsPlot";

function ResultsGraphsLayout({
  currentMetrics,
  selectedMetrics,
  handleToggleMetric,
  handleSelectAll,
  handleClearAll,
  chartData,
}) {
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="stretch"
      width="100%"
      height="100%"
    >
      {/* Metric filter toolbar */}
      <ResultsGraphsParameters
        currentMetrics={currentMetrics}
        selectedMetrics={selectedMetrics}
        handleToggleMetric={handleToggleMetric}
        handleSelectAll={handleSelectAll}
        handleClearAll={handleClearAll}
      />

      {/* Plotly chart area — bar panels + heatmap in one grid */}
      <Box display="flex" flex={1} width="100%">
        <ResultsGraphsPlot chartData={chartData} />
      </Box>
    </Box>
  );
}

ResultsGraphsLayout.propTypes = {
  currentMetrics: PropTypes.array.isRequired,
  selectedMetrics: PropTypes.array.isRequired,
  handleToggleMetric: PropTypes.func.isRequired,
  handleSelectAll: PropTypes.func.isRequired,
  handleClearAll: PropTypes.func.isRequired,
  chartData: PropTypes.object.isRequired,
};

export default ResultsGraphsLayout;
