import React from "react";
import { Box, Typography, Card, CardContent, Alert } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import InfoIcon from "@mui/icons-material/Info";
import Plot from "react-plotly.js";
import { StatBox } from "../StatBox";
import { MetricRow } from "../MetricRow";

export const NumericTab = ({ numericStats }) => {
  const theme = useTheme();

  return (
    <Box display="flex" flexDirection="column" gap={4}>
      {Object.entries(numericStats).map(([column, stats]) => (
        <Card key={column} sx={{ borderRadius: 2 }}>
          <CardContent sx={{ bgcolor: "ui.box" }}>
            {/* Title */}
            <Box display="flex" alignItems="center" mb={2}>
              <TrendingUpIcon sx={{ color: "primary.main", mr: 1 }} />
              <Typography variant="h6" fontWeight="bold">
                {column}
              </Typography>
            </Box>

            {/* Summary Stats */}
            <Box display="flex" flexWrap="wrap" gap={2} mb={3}>
              <Box flex="1 1 200px" minWidth="150px">
                <StatBox label="Mean" value={stats.mean.toFixed(2)} />
              </Box>
              <Box flex="1 1 200px" minWidth="150px">
                <StatBox label="Median" value={stats.median.toFixed(2)} />
              </Box>
              <Box flex="1 1 200px" minWidth="150px">
                <StatBox label="Std Dev" value={stats.std.toFixed(2)} />
              </Box>
              <Box flex="1 1 200px" minWidth="150px">
                <StatBox label="Unique" value={stats.n_unique} />
              </Box>
            </Box>

            {/* Two-column metrics */}
            <Box display="flex" flexWrap="wrap" gap={4}>
              {/* Distribution Metrics */}
              <Box flex="1 1 300px" minWidth="250px">
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Distribution Metrics
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <MetricRow label="Min" value={stats.min.toFixed(2)} />
                  <MetricRow label="Q1" value={stats.q1.toFixed(2)} />
                  <MetricRow
                    label="Median (Q2)"
                    value={stats.median.toFixed(2)}
                  />
                  <MetricRow label="Q3" value={stats.q3.toFixed(2)} />
                  <MetricRow label="Max" value={stats.max.toFixed(2)} />
                </Box>
              </Box>

              {/* Shape Indicators */}
              <Box flex="1 1 300px" minWidth="250px">
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Shape Indicators
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <MetricRow label="Skewness" value={stats.skew.toFixed(3)} />
                  <MetricRow
                    label="Kurtosis"
                    value={stats.kurtosis.toFixed(3)}
                  />
                  <MetricRow label="Outliers" value={stats.outliers_count} />
                  <MetricRow
                    label="Range"
                    value={(stats.max - stats.min).toFixed(2)}
                  />
                </Box>
              </Box>
            </Box>

            {/* Horizontal Boxplot Visualization */}
            <Box mt={4}>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Boxplot
              </Typography>
              <Plot
                data={[
                  {
                    x: [stats.min, stats.q1, stats.median, stats.q3, stats.max],
                    type: "box",
                    name: column,
                    orientation: "h", // ← rotated here
                    boxpoints: "suspectedoutliers",
                    marker: { color: "#8884d8" },
                    line: { color: "#212121" },
                    fillcolor: "#8884d8",
                    opacity: 0.6,
                    showlegend: false,
                  },
                ]}
                layout={{
                  paper_bgcolor: "transparent",
                  plot_bgcolor: "transparent",
                  font: { color: theme.palette.text.primary },
                  margin: { t: 10, b: 40, l: 40, r: 20 },
                  height: 220,
                  xaxis: {
                    title: "",
                    zeroline: false,
                    gridcolor:
                      theme.palette.mode === "dark" ? "#444" : "#e0e0e0",
                  },
                  yaxis: {
                    showticklabels: false,
                  },
                }}
                config={{
                  responsive: true,
                  displayModeBar: false,
                }}
                style={{ width: "100%", height: "100%" }}
              />
            </Box>

            {/* Skewness Warning */}
            {stats.skew > 1 && (
              <Alert
                severity="warning"
                icon={<InfoIcon fontSize="inherit" />}
                sx={{ mt: 3 }}
              >
                <Typography variant="body2">
                  <strong>Right-skewed distribution:</strong> Consider applying
                  a log transformation.
                </Typography>
              </Alert>
            )}
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};
