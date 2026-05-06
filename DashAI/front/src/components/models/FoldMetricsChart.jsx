import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import {
  Box,
  CircularProgress,
  Alert,
  AlertTitle,
  Paper,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import api from "../../api/api";

/**
 * FoldMetricsChart
 *
 * Displays fold-level metrics from cross-validation using interactive Plotly charts.
 * Currently shows boxplots for each metric across all folds.
 *
 * Props:
 * - runId: ID of the run to display fold metrics for
 * - metricSplit: "train", "validation", or "test"
 * - metrics: Array of metric objects with name and metadata properties
 */
export default function FoldMetricsChart({
  runId,
  metricSplit = "test",
  metrics = [],
}) {
  const theme = useTheme();
  const [foldMetrics, setFoldMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch fold metrics data
  useEffect(() => {
    if (!runId) return;

    const fetchFoldMetrics = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get(`/v1/run/${runId}/fold-metrics`, {
          params: { metric_split: metricSplit },
        });
        setFoldMetrics(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load fold metrics");
        console.error("Error fetching fold metrics:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchFoldMetrics();
  }, [runId, metricSplit]);

  // Build boxplot traces
  const createBoxplotTraces = () => {
    if (!foldMetrics) return [];

    const traces = [];
    const metricNames = Object.keys(foldMetrics).sort();

    metricNames.forEach((metricName) => {
      const metricInfo = metrics.find((m) => m.name === metricName);
      const values = foldMetrics[metricName];

      traces.push({
        y: values,
        name: metricName,
        type: "box",
        boxmean: "sd", // Show mean and standard deviation
        marker: {
          color: metricInfo?.metadata?.color || "#1f77b4",
        },
        hovertemplate:
          "<b>%{fullData.name}</b><br>" +
          "Min: %{y}<br>" +
          "Q1: %{q1}<br>" +
          "Median: %{median}<br>" +
          "Q3: %{q3}<br>" +
          "Max: %{y}<br>" +
          "<extra></extra>",
      });
    });

    return traces;
  };

  // Build layout with theme colors
  const getLayout = () => {
    const isDarkMode = theme.palette.mode === "dark";
    const textColor = isDarkMode ? "#e0e0e0" : "#424242";
    const gridColor = isDarkMode ? "#424242" : "#e0e0e0";

    return {
      title: {
        text: `Cross-Validation Fold Metrics (${metricSplit})`,
        font: { size: 14 },
      },
      yaxis: {
        title: "Metric Value",
        gridcolor: gridColor,
        titlefont: { color: textColor },
        tickfont: { color: textColor },
      },
      xaxis: {
        titlefont: { color: textColor },
        tickfont: { color: textColor },
      },
      paper_bgcolor: isDarkMode ? "#1e1e1e" : "#ffffff",
      plot_bgcolor: isDarkMode ? "#2a2a2a" : "#f5f5f5",
      font: {
        color: textColor,
        family: '"Roboto", "Helvetica", "Arial", sans-serif',
      },
      hovermode: "closest",
      margin: { l: 60, r: 30, t: 50, b: 50 },
      autosize: true,
    };
  };

  if (!runId) {
    return (
      <Alert severity="info">
        <AlertTitle>No Run Selected</AlertTitle>
        Select a run to view fold-level metrics.
      </Alert>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="warning">
        <AlertTitle>No Fold Data Available</AlertTitle>
        {error} — This run may not use cross-validation.
      </Alert>
    );
  }

  if (!foldMetrics || Object.keys(foldMetrics).length === 0) {
    return (
      <Alert severity="info">
        <AlertTitle>No Fold Metrics</AlertTitle>
        No fold-level metrics available for this run.
      </Alert>
    );
  }

  const traces = createBoxplotTraces();

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        minHeight: 300,
      }}
    >
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: "bold" }}>
        Cross-Validation Fold Analysis
      </Typography>
      <Box sx={{ flex: 1, minHeight: 0 }}>
        <Plot
          data={traces}
          layout={getLayout()}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ["select2d", "lasso2d"],
          }}
          style={{ width: "100%", height: "100%" }}
        />
      </Box>
    </Box>
  );
}

FoldMetricsChart.propTypes = {
  runId: PropTypes.number,
  metricSplit: PropTypes.oneOf(["train", "validation", "test"]),
  metrics: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      metadata: PropTypes.object,
    }),
  ),
};
