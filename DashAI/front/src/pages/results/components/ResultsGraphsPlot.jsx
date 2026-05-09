import React from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import Plot from "react-plotly.js";
import { useTranslation } from "react-i18next";

function ResultsGraphsPlot({ selectedChart, chartData }) {
  const { t } = useTranslation(["models"]);

  const traceData =
    selectedChart === "heatmap"
      ? (chartData.heatmap ?? [])
      : (chartData.bar ?? []);

  const hasData = traceData.length > 0;

  if (!hasData) {
    return (
      <Box
        flex={1}
        display="flex"
        alignItems="center"
        justifyContent="center"
        sx={{
          minHeight: 400,
          border: "1px dashed",
          borderColor: "divider",
          borderRadius: 1,
          m: 2,
        }}
      >
        <Typography color="text.secondary">
          {t("models:label.noMetricsAvailableForThisView")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box flex={1} sx={{ minHeight: 400, overflow: "hidden" }}>
      <Plot
        data={traceData}
        layout={{
          ...(chartData.generalLayout ?? {}),
          autosize: true,
          width: undefined,
        }}
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
        config={{
          responsive: true,
          displayModeBar: false,
          staticPlot: selectedChart === "heatmap",
        }}
      />
    </Box>
  );
}

ResultsGraphsPlot.propTypes = {
  selectedChart: PropTypes.string.isRequired,
  chartData: PropTypes.object.isRequired,
};

export default ResultsGraphsPlot;
