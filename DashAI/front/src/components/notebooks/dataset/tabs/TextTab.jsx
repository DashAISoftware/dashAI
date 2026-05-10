import React, { useState } from "react";
import {
  Box,
  Typography,
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
import ExportableCard from "../ExportableCard";
import { useTranslation } from "react-i18next";

export const TextTab = ({ textStats }) => {
  const theme = useTheme();
  const { t } = useTranslation(["datasets", "common"]);
  const [activeIndices, setActiveIndices] = useState({});
  return (
    <Box display="flex" flexDirection="column" gap={8}>
      {Object.entries(textStats).map(([column, stats]) => {
        const lengthData = [
          {
            label: t("datasets:label.min"),
            value: stats.min_length,
            color: theme.palette.chart.train,
          },
          {
            label: t("datasets:label.median"),
            value: stats.median_length,
            color: theme.palette.chart.test,
          },
          {
            label: t("datasets:label.avg"),
            value: stats.avg_length,
            color: theme.palette.chart.validation,
          },
          {
            label: t("datasets:label.max"),
            value: stats.max_length,
            color: theme.palette.primary.main,
          },
        ];

        const uniquePercentage = stats.unique_ratio
          ? (stats.unique_ratio * 100).toFixed(1)
          : null;

        return (
          <ExportableCard
            key={column}
            filename={`text_${column}`}
            exportData={{ column, ...stats }}
            data-column-card={column}
            sx={{ borderRadius: 2 }}
          >
            <CardContent sx={{ bgcolor: theme.palette.ui.panelDark }}>
              {/* Title */}
              <Box display="flex" alignItems="center" mb={4}>
                <TextFieldsIcon sx={{ color: "primary.main", mr: 2 }} />
                <Typography variant="h6" fontWeight="bold">
                  {column}
                </Typography>

                {uniquePercentage && (
                  <Tooltip title={t("datasets:label.uniquenessFormula")} arrow>
                    <Chip
                      label={t("datasets:label.uniquePercentage", {
                        percentage: uniquePercentage,
                      })}
                      size="small"
                      sx={{
                        ml: 4,
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
                <Alert severity="warning" sx={{ mb: 6 }}>
                  {t("datasets:label.lowUniquenessWarning")}
                </Alert>
              )}

              {/* Summary Stats (StatBoxes) */}
              <Box display="flex" flexWrap="wrap" gap={4} mb={6}>
                <Box flex="1 1 200px" minWidth="150px">
                  <StatBox
                    label={t("datasets:label.avgLength")}
                    value={Math.round(stats.avg_length)}
                  />
                </Box>

                <Box flex="1 1 200px" minWidth="150px">
                  <StatBox
                    label={t("datasets:label.medianLength")}
                    value={stats.median_length}
                  />
                </Box>

                {stats.avg_word_count && (
                  <Box flex="1 1 200px" minWidth="150px">
                    <StatBox
                      label={t("datasets:label.avgWordCount")}
                      value={Math.round(stats.avg_word_count)}
                    />
                  </Box>
                )}

                <Box flex="1 1 200px" minWidth="150px">
                  <StatBox
                    label={t("datasets:label.uniqueValues")}
                    value={stats.unique_count}
                  />
                </Box>
              </Box>

              {/* Two-column metric grouping */}
              <Box display="flex" flexWrap="wrap" gap={8}>
                <Box flex="1 1 300px" minWidth="250px">
                  <Typography
                    variant="subtitle2"
                    fontWeight="bold"
                    color="text.primary"
                    gutterBottom
                    sx={{ fontSize: "0.875rem", textTransform: "uppercase" }}
                  >
                    {t("datasets:label.lengthMetrics")}
                  </Typography>

                  <Box display="flex" gap={8}>
                    {/* Column 1 */}
                    <Box display="flex" flexDirection="column" gap={2} flex="1">
                      <MetricRow
                        label={t("datasets:label.minLength")}
                        value={stats.min_length}
                      />
                      <MetricRow
                        label={t("datasets:label.medianLength")}
                        value={stats.median_length}
                      />
                      <MetricRow
                        label={t("datasets:label.mean")}
                        value={stats.avg_length?.toFixed(1)}
                      />
                    </Box>

                    {/* Column 2 */}
                    <Box display="flex" flexDirection="column" gap={2} flex="1">
                      <MetricRow
                        label={t("datasets:label.maxLength")}
                        value={stats.max_length}
                      />
                      <MetricRow
                        label={t("datasets:label.range")}
                        value={stats.max_length - stats.min_length}
                      />
                    </Box>
                  </Box>
                </Box>
              </Box>

              {/* Plot: Length Distribution */}
              <Box mt={8}>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  {t("datasets:label.lengthDistribution")}
                </Typography>
                <Box sx={{ width: "100%", height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={lengthData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" />
                      <YAxis />
                      <RechartsTooltip
                        cursor={false}
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          borderRadius: 4,
                          color: theme.palette.text.primary,
                          border: `1px solid ${theme.palette.divider}`,
                        }}
                        labelStyle={{ color: theme.palette.text.primary }}
                      />
                      <Bar
                        dataKey="value"
                        fill="#8884d8"
                        name={t("common:value")}
                        activeBar={false}
                        onMouseEnter={(_, index) =>
                          setActiveIndices((prev) => ({
                            ...prev,
                            [column]: index,
                          }))
                        }
                        onMouseLeave={() =>
                          setActiveIndices((prev) => ({
                            ...prev,
                            [column]: null,
                          }))
                        }
                      >
                        {lengthData.map((entry, index) => {
                          const activeIndex = activeIndices[column] ?? null;
                          return (
                            <Cell
                              key={index}
                              fill="#8884d8"
                              fillOpacity={
                                index === activeIndex
                                  ? 1
                                  : activeIndex !== null
                                    ? 0.5
                                    : 0.7
                              }
                            />
                          );
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            </CardContent>
          </ExportableCard>
        );
      })}
    </Box>
  );
};
