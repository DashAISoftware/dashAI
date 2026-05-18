import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import {
  Box,
  CircularProgress,
  Alert,
  AlertTitle,
  ToggleButton,
  ToggleButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import api from "../../api/api";
import ResultsGraphsParameters from "../../pages/results/components/ResultsGraphsParameters";

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
  isNestedCV = false,
}) {
  const theme = useTheme();
  const [allRepetitionsData, setAllRepetitionsData] = useState(null);
  const [selectedRepetition, setSelectedRepetition] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chartType, setChartType] = useState("boxplot");
  // "outer" = nested CV evaluation folds, "final" = HPO final training folds
  const [foldScope, setFoldScope] = useState("outer");
  // Track selected metrics (array of metric names)
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  // Ref to always access current selectedRepetition inside async callbacks
  const selectedRepetitionRef = useRef(selectedRepetition);
  useEffect(() => {
    selectedRepetitionRef.current = selectedRepetition;
  }, [selectedRepetition]);

  // Fetch fold metrics data
  useEffect(() => {
    if (!runId) return;

    const fetchFoldMetrics = async () => {
      setLoading(true);
      setError(null);
      setAllRepetitionsData(null);
      const previousRepetition = selectedRepetitionRef.current;
      try {
        // outer-fold-metrics: nested CV evaluation folds
        // fold-metrics: HPO final training folds (default for non-nested)
        const endpoint =
          isNestedCV && foldScope === "outer"
            ? `/v1/run/${runId}/outer-fold-metrics`
            : `/v1/run/${runId}/fold-metrics`;
        const response = await api.get(endpoint, {
          params: { metric_split: metricSplit },
        });

        // Check if response has multiple repetitions (keys like "rep_0", "rep_1", etc.)
        const hasRepetitions =
          response.data &&
          Object.keys(response.data).some((key) => key.startsWith("rep_"));

        if (hasRepetitions) {
          // Extract repetition keys (e.g., "rep_0", "rep_1", etc.)
          const repKeys = Object.keys(response.data)
            .filter((key) => key.startsWith("rep_"))
            .sort((a, b) => {
              const numA = parseInt(a.split("_")[1]);
              const numB = parseInt(b.split("_")[1]);
              return numA - numB;
            });

          setAllRepetitionsData(response.data);
          // Set default to first repetition
          if (repKeys.length > 0) {
            // Keep current repetition if valid, otherwise default to averaged
            const isValidRep =
              previousRepetition === "averaged" ||
              repKeys.includes(previousRepetition);
            setSelectedRepetition(isValidRep ? previousRepetition : "averaged");
          }
        } else {
          // Single CV (no repetitions) - treat as rep_0
          setAllRepetitionsData({ rep_0: response.data });
          setSelectedRepetition("rep_0");
        }

        // Initialize all metrics as selected
        if (response.data) {
          const metricsData =
            hasRepetitions && response.data.rep_0
              ? response.data.rep_0
              : response.data;
          const allMetricNames = Object.keys(metricsData);
          setSelectedMetrics(allMetricNames);
        }
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load fold metrics");
        console.error("Error fetching fold metrics:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchFoldMetrics();
  }, [runId, metricSplit, foldScope, isNestedCV]);

  // Compute per-fold average across all repetitions
  const computeAveragedData = () => {
    if (!allRepetitionsData) return null;
    const reps = Object.keys(allRepetitionsData).filter((k) =>
      k.startsWith("rep_"),
    );
    if (reps.length === 0) return null;

    const metricNames = Object.keys(allRepetitionsData[reps[0]]);
    const averaged = {};

    metricNames.forEach((metric) => {
      const nFolds = allRepetitionsData[reps[0]][metric].length;
      averaged[metric] = Array.from({ length: nFolds }, (_, foldIdx) => {
        const vals = reps.map(
          (rep) => allRepetitionsData[rep][metric][foldIdx] ?? 0,
        );
        return vals.reduce((a, b) => a + b, 0) / vals.length;
      });
    });

    return averaged;
  };

  // Concatenate all fold values across all repetitions (used for Q-Q plot)
  const computeConcatenatedData = () => {
    if (!allRepetitionsData) return null;
    const reps = Object.keys(allRepetitionsData).filter((k) =>
      k.startsWith("rep_"),
    );
    if (reps.length === 0) return null;

    const metricNames = Object.keys(allRepetitionsData[reps[0]]);
    const concatenated = {};
    metricNames.forEach((metric) => {
      concatenated[metric] = reps.flatMap(
        (rep) => allRepetitionsData[rep][metric],
      );
    });
    return concatenated;
  };

  // Build boxplot traces
  const createBoxplotTraces = () => {
    if (!allRepetitionsData || !selectedRepetition) return [];

    const foldMetrics =
      selectedRepetition === "averaged"
        ? computeAveragedData()
        : allRepetitionsData[selectedRepetition];
    if (!foldMetrics) return [];

    const traces = [];
    const metricNames = Object.keys(foldMetrics).sort();

    metricNames.forEach((metricName, index) => {
      // Skip if metric is not selected
      if (!selectedMetrics.includes(metricName)) return;

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
          "<b>%{fullData.name}</b><br>Value: %{y:.4f}<extra></extra>",
      });
    });

    return traces;
  };

  // Build line chart traces (one line per metric showing fold progression)
  const createLineTraces = () => {
    if (!allRepetitionsData || !selectedRepetition) return [];

    const foldMetrics =
      selectedRepetition === "averaged"
        ? computeAveragedData()
        : allRepetitionsData[selectedRepetition];
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
      // Skip if metric is not selected
      if (!selectedMetrics.includes(metricName)) return;

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

  // Calculate Q-Q plot data
  const calculateNormalQuantiles = (data) => {
    const sorted = [...data].sort((a, b) => a - b);
    const n = sorted.length;
    const quantiles = [];
    for (let i = 0; i < n; i++) {
      // Use median rank to calculate theoretical quantile
      const p = (i + 0.5) / n;
      const q = Math.sqrt(2) * errorInverse(2 * p - 1);
      quantiles.push({ sample: sorted[i], theoretical: q });
    }
    return quantiles;
  };

  // Approximate inverse error function (Abramowitz & Stegun, more accurate)
  const errorInverse = (x) => {
    const a = 0.147;
    const ln = Math.log(1 - x * x);
    const term1 = 2 / (Math.PI * a) + ln / 2;
    const term2 = ln / a;
    return Math.sign(x) * Math.sqrt(Math.sqrt(term1 * term1 - term2) - term1);
  };

  // Build Q-Q plot traces
  const createQQPlotTraces = () => {
    if (!allRepetitionsData || !selectedRepetition) return [];

    // For Q-Q, concatenate all repetitions to maximize points
    // Averaging would reduce points and hide the variability we want to assess
    const foldMetrics =
      selectedRepetition === "averaged"
        ? computeConcatenatedData()
        : allRepetitionsData[selectedRepetition];
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

    let allTheoreticalValues = [];
    let allSampleValues = [];

    metricNames.forEach((metricName, index) => {
      if (!selectedMetrics.includes(metricName)) return;

      const values = foldMetrics[metricName];
      if (values.length < 3) return; // Q-Q plot needs at least 3 points

      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      const std = Math.sqrt(
        values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) /
          values.length,
      );

      const quantileData = calculateNormalQuantiles(values);
      const sampleQuantiles = quantileData.map((q) => q.sample);
      const theoreticalQuantiles = quantileData.map(
        (q) => mean + q.theoretical * std,
      );

      allTheoreticalValues.push(...theoreticalQuantiles);
      allSampleValues.push(...sampleQuantiles);

      // Sample points
      traces.push({
        x: theoreticalQuantiles,
        y: sampleQuantiles,
        name: metricName,
        type: "scatter",
        mode: "markers",
        marker: {
          size: 8,
          color:
            metrics.find((m) => m.name === metricName)?.metadata?.color ||
            themeColors[index % themeColors.length],
        },
        hovertemplate:
          "<b>%{fullData.name}</b><br>" +
          "Theoretical: %{x:.3f}<br>" +
          "Sample: %{y:.3f}<br>" +
          "<extra></extra>",
      });
    });

    // Reference diagonal y=x over theoretical quantile range
    if (allTheoreticalValues.length > 0) {
      const tMin = Math.min(...allTheoreticalValues);
      const tMax = Math.max(...allTheoreticalValues);
      const padding = (tMax - tMin) * 0.1;

      traces.push({
        x: [tMin - padding, tMax + padding],
        y: [tMin - padding, tMax + padding],
        name: "Reference (Normal)",
        type: "scatter",
        mode: "lines",
        line: {
          color: theme.palette.mode === "dark" ? "#ff7f0e" : "#ff7f0e",
          dash: "solid",
          width: 3,
        },
        hoverinfo: "skip",
        showlegend: true,
      });
    }

    return traces;
  };

  // Build histogram traces
  const createHistogramTraces = () => {
    if (!allRepetitionsData || !selectedRepetition) return [];

    const foldMetrics =
      selectedRepetition === "averaged"
        ? computeAveragedData()
        : allRepetitionsData[selectedRepetition];
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
      if (!selectedMetrics.includes(metricName)) return;

      const values = foldMetrics[metricName];

      traces.push({
        x: values,
        name: metricName,
        type: "histogram",
        nbinsx: Math.max(5, Math.ceil(Math.sqrt(values.length))),
        marker: {
          color:
            metrics.find((m) => m.name === metricName)?.metadata?.color ||
            themeColors[index % themeColors.length],
          opacity: 0.7,
        },
        hovertemplate:
          "<b>%{fullData.name}</b><br>" +
          "Range: [%{x}, %{xbingroup}]<br>" +
          "Count: %{y}<br>" +
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
      margin: { l: 30, r: 0, t: 40, b: 50 },
      autosize: true,
      showlegend: false,
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

    if (chartType === "qq") {
      return {
        ...baseLayout,
        showlegend: true,
        title: {
          text:
            selectedRepetition === "averaged"
              ? `Q-Q Plot - All Repetitions (${metricSplit})`
              : `Q-Q Plot - Normality Assessment (${metricSplit})`,
          font: { size: 14 },
        },
        xaxis: {
          title: "Theoretical Quantiles",
          gridcolor: gridColor,
          titlefont: { color: textColor },
          tickfont: { color: textColor },
        },
        yaxis: {
          title: "Sample Quantiles",
          gridcolor: gridColor,
          titlefont: { color: textColor },
          tickfont: { color: textColor },
        },
      };
    }

    if (chartType === "histogram") {
      return {
        ...baseLayout,
        title: {
          text: `Distribution Histogram (${metricSplit})`,
          font: { size: 14 },
        },
        xaxis: {
          title: "Metric Value",
          gridcolor: gridColor,
          titlefont: { color: textColor },
          tickfont: { color: textColor },
        },
        yaxis: {
          title: "Frequency",
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

  // Get available metrics from current data
  const getAvailableMetrics = () => {
    if (!allRepetitionsData || !selectedRepetition) return [];
    const foldMetrics =
      selectedRepetition === "averaged"
        ? computeAveragedData()
        : allRepetitionsData[selectedRepetition];
    return foldMetrics ? Object.keys(foldMetrics).sort() : [];
  };

  const availableMetrics = getAvailableMetrics();

  // Handle selecting all metrics
  const handleSelectAll = () => {
    setSelectedMetrics(availableMetrics);
  };

  // Handle deselecting all metrics
  const handleClearAll = () => {
    setSelectedMetrics([]);
  };

  // Handle individual metric toggle
  const handleToggleMetric = (metricName) => {
    setSelectedMetrics((prev) => {
      if (prev.includes(metricName)) {
        return prev.filter((m) => m !== metricName);
      }
      const next = new Set([...prev, metricName]);
      return availableMetrics.filter((m) => next.has(m));
    });
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
    chartType === "line"
      ? createLineTraces()
      : chartType === "qq"
        ? createQQPlotTraces()
        : chartType === "histogram"
          ? createHistogramTraces()
          : createBoxplotTraces();
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
        minHeight: 400,
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 1,
          gap: 1.5,
          px: 1.5,
          py: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: "bold" }}>
            CV Fold Analysis
          </Typography>
          {isNestedCV && (
            <ToggleButtonGroup
              exclusive
              value={foldScope}
              onChange={(_, v) => {
                if (v) setFoldScope(v);
              }}
              size="small"
              sx={{ height: 28 }}
            >
              <ToggleButton
                value="outer"
                title="Outer folds — reliable generalization estimate from nested CV"
                sx={{ px: 0.75, py: 0, fontSize: "0.75rem" }}
              >
                Outer
              </ToggleButton>
              <ToggleButton
                value="final"
                title="Folds used during final HPO training to produce the model"
                sx={{ px: 0.75, py: 0, fontSize: "0.75rem" }}
              >
                HPO
              </ToggleButton>
            </ToggleButtonGroup>
          )}
          {availableReps.length > 1 && (
            <FormControl sx={{ minWidth: 140 }} size="small">
              <InputLabel sx={{ fontSize: "0.85rem" }}>Rep.</InputLabel>
              <Select
                value={selectedRepetition ?? ""}
                label="Rep."
                onChange={(e) => setSelectedRepetition(e.target.value)}
                sx={{ fontSize: "0.85rem" }}
              >
                <MenuItem value="averaged">
                  {chartType === "qq" ? "All repetitions" : "Averaged"}
                </MenuItem>
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
          sx={{ height: 28 }}
        >
          <ToggleButton
            value="boxplot"
            title="Boxplot with statistics"
            sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
          >
            Boxplot
          </ToggleButton>
          <ToggleButton
            value="line"
            title="Line chart showing fold progression"
            sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
          >
            Lines
          </ToggleButton>
          <ToggleButton
            value="qq"
            title="Q-Q plot for normality assessment"
            sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
          >
            Q-Q
          </ToggleButton>
          <ToggleButton
            value="histogram"
            title="Distribution histogram"
            sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
          >
            Hist
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <Box sx={{ display: "flex", flex: 1, minHeight: 0, width: "100%" }}>
        {/* Metrics sidebar using shared component */}
        <ResultsGraphsParameters
          currentMetrics={availableMetrics}
          selectedMetrics={selectedMetrics}
          handleToggleMetric={handleToggleMetric}
          handleSelectAll={handleSelectAll}
          handleClearAll={handleClearAll}
        />

        {/* Chart area */}
        <Box sx={{ flex: 1, minHeight: 0, width: "100%", p: 0.5 }}>
          <Plot
            data={traces}
            layout={getLayout()}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: [
                "select2d",
                "lasso2d",
                "zoomIn2d",
                "autoScale2d",
              ],
            }}
            style={{ width: "100%", height: "100%" }}
          />
        </Box>
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
  isNestedCV: PropTypes.bool,
};
