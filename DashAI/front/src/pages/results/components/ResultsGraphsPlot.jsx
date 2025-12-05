import React from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";
import Plot from "react-plotly.js";

function ResultsGraphsPlot({ selectedChart, chartData }) {
  return (
    <Box width="100%" sx={{ flex: 1 }}>
      <Plot
        data={
          selectedChart === "radar"
            ? chartData.radarValues
            : selectedChart === "bar"
              ? chartData.barValues
              : selectedChart === "pie"
                ? chartData.pieValues
                : []
        }
        layout={{
          ...(selectedChart === "pie"
            ? chartData.pieLayout
            : chartData.generalLayout),
          autosize: true,
          width: undefined,
        }}
        useResizeHandler={true}
        style={{ width: "100%", height: "100%" }}
      />
    </Box>
  );
}

ResultsGraphsPlot.propTypes = {
  selectedChart: PropTypes.string.isRequired,
  chartData: PropTypes.object.isRequired,
};

export default ResultsGraphsPlot;
