import React from "react";
import { Box, Typography, Card, CardContent, Alert } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import InfoIcon from "@mui/icons-material/Info";
import Plot from "react-plotly.js";
import { StatBox } from "../StatBox";
import { MetricRow } from "../MetricRow";
import { Trans, useTranslation } from "react-i18next";

export const NumericTab = ({ numericStats }) => {
  const { t } = useTranslation(["datasets"]);
  const theme = useTheme();

  return (
    <Box display="flex" flexDirection="column" gap={4}>
      {Object.entries(numericStats).map(([column, stats]) => (
        <Card key={column} data-column-card={column} sx={{ borderRadius: 2 }}>
          <CardContent sx={{ bgcolor: theme.palette.ui.box }}>
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
                <StatBox
                  label={t("datasets:label.mean")}
                  value={stats.mean.toFixed(2)}
                />
              </Box>
              <Box flex="1 1 200px" minWidth="150px">
                <StatBox
                  label={t("datasets:label.median")}
                  value={stats.median.toFixed(2)}
                />
              </Box>
              <Box flex="1 1 200px" minWidth="150px">
                <StatBox
                  label={t("datasets:label.stdDev")}
                  value={stats.std.toFixed(2)}
                />
              </Box>
              <Box flex="1 1 200px" minWidth="150px">
                <StatBox
                  label={t("datasets:label.unique")}
                  value={stats.n_unique}
                />
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
                  {t("datasets:label.distributionMetrics")}
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <MetricRow
                    label={t("datasets:label.min")}
                    value={stats.min.toFixed(2)}
                  />
                  <MetricRow
                    label={t("datasets:label.q1")}
                    value={stats.q1.toFixed(2)}
                  />
                  <MetricRow
                    label={t("datasets:label.median")}
                    value={stats.median.toFixed(2)}
                  />
                  <MetricRow
                    label={t("datasets:label.q3")}
                    value={stats.q3.toFixed(2)}
                  />
                  <MetricRow
                    label={t("datasets:label.max")}
                    value={stats.max.toFixed(2)}
                  />
                </Box>
              </Box>

              {/* Shape Indicators */}
              <Box flex="1 1 300px" minWidth="250px">
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  {t("datasets:label.shapeIndicators")}
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <MetricRow
                    label={t("datasets:label.skewness")}
                    value={stats.skew.toFixed(3)}
                  />
                  <MetricRow
                    label={t("datasets:label.kurtosis")}
                    value={stats.kurtosis.toFixed(3)}
                  />
                  <MetricRow
                    label={t("datasets:label.outliers")}
                    value={stats.outliers_count}
                  />
                  <MetricRow
                    label={t("datasets:label.range")}
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
                {t("datasets:label.boxplot")}
              </Typography>
              <Plot
                data={[
                  {
                    x: [stats.min, stats.q1, stats.median, stats.q3, stats.max],
                    type: "box",
                    name: column,
                    orientation: "h", // ← rotated here
                    boxpoints: "suspectedoutliers",
                    marker: { color: theme.palette.info.main },
                    line: { color: theme.palette.text.secondary },
                    fillcolor: theme.palette.info.main,
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
                      theme.palette.mode === "dark"
                        ? theme.palette.ui.borderLight
                        : theme.palette.ui.border,
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
                  <Trans i18nKey="datasets:label.rightSkewedWarning">
                    <strong>Right-skewed distribution:</strong> Consider
                    applying a log transformation.
                  </Trans>
                </Typography>
              </Alert>
            )}
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};
