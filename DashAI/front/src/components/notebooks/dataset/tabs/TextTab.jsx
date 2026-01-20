import React from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  Tooltip,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import TextFieldsIcon from "@mui/icons-material/TextFields";
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Bar,
  Cell,
} from "recharts";
import { StatBox } from "../StatBox";
import { MetricRow } from "../MetricRow";

export const TextTab = ({ textStats }) => {
  const theme = useTheme();
  return (
    <Box display="flex" flexDirection="column" gap={4}>
      {Object.entries(textStats).map(([column, stats]) => {
        const lengthData = [
          {
            label: "Min",
            value: stats.min_length,
            color: theme.palette.success.light,
          },
          {
            label: "Median",
            value: stats.median_length,
            color: theme.palette.info.main,
          },
          {
            label: "Avg",
            value: stats.avg_length,
            color: theme.palette.warning.main,
          },
          {
            label: "Max",
            value: stats.max_length,
            color: theme.palette.error.main,
          },
        ];

        const uniquePercentage = stats.unique_ratio
          ? (stats.unique_ratio * 100).toFixed(1)
          : null;

        return (
          <Card key={column} sx={{ borderRadius: 2 }}>
            <CardContent sx={{ bgcolor: theme.palette.ui.panelDark }}>
              {/* Title */}
              <Box display="flex" alignItems="center" mb={2}>
                <TextFieldsIcon sx={{ color: "primary.main", mr: 1 }} />
                <Typography variant="h6" fontWeight="bold">
                  {column}
                </Typography>

                {uniquePercentage && (
                  <Tooltip title={"Uniqueness = (Unique ÷ Total) × 100"} arrow>
                    <Chip
                      label={`${uniquePercentage}% unique`}
                      size="small"
                      sx={{
                        ml: 2,
                        bgcolor:
                          uniquePercentage > 90
                            ? theme.palette.success.main
                            : uniquePercentage > 30
                              ? theme.palette.warning.main
                              : theme.palette.error.main,
                        color: "white",
                        cursor: "default",
                      }}
                    />
                  </Tooltip>
                )}
              </Box>

              {parseFloat(uniquePercentage) <= 30 && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                  Warning: This text column has a very low uniqueness ratio.
                  This may be a categorical variable misclassified as text,
                  which could lead to analysis issues.
                </Alert>
              )}

              {/* Summary Stats (StatBoxes) */}
              <Box display="flex" flexWrap="wrap" gap={2} mb={3}>
                <Box flex="1 1 200px" minWidth="150px">
                  <StatBox
                    label="Avg Length"
                    value={Math.round(stats.avg_length)}
                  />
                </Box>

                <Box flex="1 1 200px" minWidth="150px">
                  <StatBox label="Median Length" value={stats.median_length} />
                </Box>

                {stats.avg_word_count && (
                  <Box flex="1 1 200px" minWidth="150px">
                    <StatBox
                      label="Avg Word Count"
                      value={Math.round(stats.avg_word_count)}
                    />
                  </Box>
                )}

                <Box flex="1 1 200px" minWidth="150px">
                  <StatBox label="Unique Values" value={stats.unique_count} />
                </Box>
              </Box>

              {/* Two-column metric grouping */}
              <Box display="flex" flexWrap="wrap" gap={4}>
                <Box flex="1 1 300px" minWidth="250px">
                  <Typography
                    variant="subtitle2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Length Metrics
                  </Typography>

                  <Box display="flex" gap={4}>
                    {/* Column 1 */}
                    <Box display="flex" flexDirection="column" gap={1} flex="1">
                      <MetricRow label="Min Length" value={stats.min_length} />
                      <MetricRow label="Median" value={stats.median_length} />
                      <MetricRow
                        label="Mean"
                        value={stats.avg_length?.toFixed(1)}
                      />
                    </Box>

                    {/* Column 2 */}
                    <Box display="flex" flexDirection="column" gap={1} flex="1">
                      <MetricRow label="Max Length" value={stats.max_length} />
                      <MetricRow
                        label="Range"
                        value={stats.max_length - stats.min_length}
                      />
                    </Box>
                  </Box>
                </Box>
              </Box>

              {/* Plot: Length Distribution */}
              <Box mt={4}>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Length Distribution
                </Typography>
                <Box sx={{ width: "100%", height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={lengthData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" />
                      <YAxis />
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          borderRadius: 4,
                          color: theme.palette.text.primary,
                          border: `1px solid ${theme.palette.divider}`,
                        }}
                        labelStyle={{ color: theme.palette.text.primary }}
                      />
                      <Bar dataKey="value" fill="rgba(136, 132, 216, 0.7)" />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
};
