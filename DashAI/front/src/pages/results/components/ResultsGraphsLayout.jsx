import React from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";

import ResultsGraphsSelection from "./ResultsGraphsSelection";
import ResultsGraphsParameters from "./ResultsGraphsParameters";
import ResultsGraphsPlot from "./ResultsGraphsPlot";

function ResultsGraphsLayout({
  selectedChart,
  handleChangeChart,
  selectedSplit,
  handleChangeSplit,
  availableMetrics,
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
      {/* Chart type selector */}
      <ResultsGraphsSelection
        selectedChart={selectedChart}
        handleChangeChart={handleChangeChart}
      />

      <Box display="flex" flex={1} width="100%">
        {/* Split + metric filter sidebar */}
        <ResultsGraphsParameters
          selectedSplit={selectedSplit}
          handleChangeSplit={handleChangeSplit}
          availableMetrics={availableMetrics}
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
      </Box>
    </Box>
  );
}

ResultsGraphsLayout.propTypes = {
  selectedChart: PropTypes.string.isRequired,
  handleChangeChart: PropTypes.func.isRequired,
  selectedSplit: PropTypes.string.isRequired,
  handleChangeSplit: PropTypes.func.isRequired,
  availableMetrics: PropTypes.shape({
    train: PropTypes.array,
    validation: PropTypes.array,
    test: PropTypes.array,
  }).isRequired,
  selectedMetrics: PropTypes.array.isRequired,
  handleToggleMetric: PropTypes.func.isRequired,
  handleSelectAll: PropTypes.func.isRequired,
  handleClearAll: PropTypes.func.isRequired,
  chartData: PropTypes.object.isRequired,
};

export default ResultsGraphsLayout;
