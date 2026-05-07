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
  ToggleButton,
  ToggleButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import api from "../../api/api";

/**
 * FoldMetricsChart
 *
 * Displays fold-level metrics from cross-validation using interactive Plotly charts.
 * Supports boxplots and line charts for visualizing fold-level performance.
 * For repeated cross-validation, allows selecting which repetition to display.
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
  const [allRepetitionsData, setAllRepetitionsData] = useState(null);
  const [selectedRepetition, setSelectedRepetition] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chartType, setChartType] = useState("boxplot");

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

        // Check if response has multiple repetitions (keys like "rep_0", "rep_1", etc.)
        const hasRepetitions =
          response.data &&
          Object.keys(response.data).some((key) => key.startsWith("rep_"));

        if (hasRepetitions) {
          // Extract repetition numbers from keys
          const reps = Object.keys(response.data)
            .filter((key) => key.startsWith("rep_"))
            .map((key) => parseInt(key.split("_")[1]))
            .sort((a, b) => a - b);

          setAllRepetitionsData(response.data);
          // Set default to first repetition
          if (reps.length > 0) {
            setSelectedRepetition(`rep_${reps[0]}`);
          }
        } else {
          // Single CV (no repetitions) - treat as rep_0
          setAllRepetitionsData({ rep_0: response.data });
          setSelectedRepetition("rep_0");
        }
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
    if (!allRepetitionsData || !selectedRepetition) return [];

    const foldMetrics = allRepetitionsData[selectedRepetition];
    if (!foldMetrics) return [];

    const traces = [];
    const metricNames = Object.keys(foldMetrics).sort();

    metricNames.forEach((metricName, index) => {
      const metricInfo = metrics.find((m) => m.name === metricName);
      const values = foldMetrics[metricName];

      const themeColors = [
        theme.palette.primary.main,
        theme.palette.secondary.main,
        theme.palette.success.main,
        theme.palette.warning.main,
        theme.palette.error.main,
      ];

      traces.push({
        y: values,
        name: metricName,
        type: "box",
        boxmean: "sd", // Show mean and standard deviation
        marker: {
          color:
            metricInfo?.metadata?.color ||
            themeColors[index % themeColors.length],
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

  // Build line chart traces (one line per metric showing fold progression)
  const createLineTraces = () => {
    if (!allRepetitionsData || !selectedRepetition) return [];

    const foldMetrics = allRepetitionsData[selectedRepetition];
    if (!foldMetrics) return [];

    const traces = [];
    const metricNames = Object.keys(foldMetrics).sort();

    const themeColors = [
      theme.palette.primary.main,
      theme.palette.secondary.main,
      theme.palette.success.main,
      theme.palette.warning.main,
      theme.palette.error.main,
    ];

    metricNames.forEach((metricName, index) => {
      const metricInfo = metrics.find((m) => m.name === metricName);
      const values = foldMetrics[metricName];
      const foldNumbers = Array.from(
        { length: values.length },
        (_, i) => i + 1,
      );

      traces.push({
        x: foldNumbers,
        y: values,
        name: metricName,
        type: "scatter",
        mode: "lines+markers",
        line: {
          color:
            metricInfo?.metadata?.color ||
            themeColors[index % themeColors.length],
          width: 2,
        },
        marker: {
          size: 6,
          color:
            metricInfo?.metadata?.color ||
            themeColors[index % themeColors.length],
        },
        hovertemplate:
          "<b>%{fullData.name}</b><br>" +
          "Fold: %{x}<br>" +
          "Value: %{y:.4f}<br>" +
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

    const baseLayout = {
      yaxis: {
        title: "Metric Value",
        gridcolor: gridColor,
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

    if (chartType === "line") {
      return {
        ...baseLayout,
        title: {
          text: `Cross-Validation Fold Progression (${metricSplit})`,
          font: { size: 14 },
        },
        xaxis: {
          title: "Fold Number",
          gridcolor: gridColor,
          titlefont: { color: textColor },
          tickfont: { color: textColor },
        },
      };
    }

    return {
      ...baseLayout,
      title: {
        text: `Cross-Validation Fold Metrics (${metricSplit})`,
        font: { size: 14 },
      },
      xaxis: {
        titlefont: { color: textColor },
        tickfont: { color: textColor },
      },
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

  if (!allRepetitionsData || !selectedRepetition) {
    return (
      <Alert severity="info">
        <AlertTitle>No Fold Metrics</AlertTitle>
        No fold-level metrics available for this run.
      </Alert>
    );
  }

  const traces =
    chartType === "line" ? createLineTraces() : createBoxplotTraces();
  const availableReps = allRepetitionsData
    ? Object.keys(allRepetitionsData)
        .filter((key) => key.startsWith("rep_"))
        .sort((a, b) => {
          const numA = parseInt(a.split("_")[1]);
          const numB = parseInt(b.split("_")[1]);
          return numA - numB;
        })
    : [];

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
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
          gap: 2,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
            Cross-Validation Fold Analysis
          </Typography>
          {availableReps.length > 1 && (
            <FormControl sx={{ minWidth: 180 }} size="small">
              <InputLabel>Repetition</InputLabel>
              <Select
                value={selectedRepetition ?? ""}
                label="Repetition"
                onChange={(e) => setSelectedRepetition(e.target.value)}
              >
                {availableReps.map((rep) => {
                  const repNum = parseInt(rep.split("_")[1]);
                  return (
                    <MenuItem key={rep} value={rep}>
                      Repetition {repNum + 1}
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>
          )}
        </Box>
        <ToggleButtonGroup
          exclusive
          value={chartType}
          onChange={(_, newChartType) => {
            if (newChartType) setChartType(newChartType);
          }}
          size="small"
        >
          <ToggleButton value="boxplot" title="Boxplot with statistics">
            Boxplot
          </ToggleButton>
          <ToggleButton
            value="line"
            title="Line chart showing fold progression"
          >
            Lines
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>
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
