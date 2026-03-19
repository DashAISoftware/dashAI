import React from "react";
import { Box, Typography, Card, CardContent } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import TitleIcon from "@mui/icons-material/Title";
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { StatBox } from "../StatBox";
import { useTranslation } from "react-i18next";

export const CategoricalTab = ({ categoricalStats }) => {
  const { t } = useTranslation(["datasets", "common"]);
  const theme = useTheme();

  return (
    <Box display="flex" flexDirection="column" gap={4}>
      {Object.entries(categoricalStats).map(([column, stats]) => (
        <Card key={column} sx={{ borderRadius: 2 }}>
          <CardContent sx={{ bgcolor: theme.palette.ui.box }}>
            {/* Header */}
            <Box display="flex" alignItems="center" mb={2}>
              <TitleIcon sx={{ color: "primary.main", mr: 1 }} />
              <Typography variant="h6" fontWeight="bold">
                {column}
              </Typography>
            </Box>

            {/* Summary Stats */}
            <Box display="flex" flexWrap="wrap" gap={2} mb={4}>
              <Box flex="1 1 300px" minWidth="250px">
                <StatBox
                  label={t("datasets:label.uniqueValues")}
                  value={stats.n_unique}
                />
              </Box>
              <Box flex="1 1 300px" minWidth="250px">
                <StatBox
                  label={t("datasets:label.mostFrequent")}
                  value={stats.most_frequent}
                />
              </Box>
              <Box flex="1 1 300px" minWidth="250px">
                <StatBox
                  label={t("datasets:label.topValueCount")}
                  value={stats.most_frequent_count}
                />
              </Box>
            </Box>

            {/* Charts */}
            <Box display="flex" flexWrap="wrap" gap={4}>
              {/* Value Distribution */}
              <Box flex="1 1 400px" minWidth="300px">
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  {t("datasets:label.valueDistribution")}
                </Typography>
                <Box sx={{ width: "100%", height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={stats.top_5}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="value"
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          borderRadius: 4,
                          color: theme.palette.text.primary,
                          border: `1px solid ${theme.palette.divider}`,
                        }}
                        labelStyle={{ color: theme.palette.text.primary }}
                      />
                      <Bar
                        dataKey="count"
                        fill="rgba(136, 132, 216, 0.7)"
                        name={t("common:count")}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Box>

              {/* Proportion */}
              <Box flex="1 1 400px" minWidth="300px">
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  {t("datasets:label.proportion")}
                </Typography>
                <Box sx={{ width: "100%", height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={stats.top_5}
                        dataKey="count"
                        nameKey="value"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label
                      >
                        {stats.top_5.map((entry, index) => (
                          <Cell
                            key={`cat-${entry.value}`}
                            fill={
                              [
                                theme.palette.secondary.main,
                                theme.palette.info.main,
                                theme.palette.primary.main,
                                theme.palette.success.light,
                                theme.palette.warning.main,
                              ][index]
                            }
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          borderRadius: 4,
                          border: `1px solid ${theme.palette.divider}`,
                        }}
                        labelStyle={{ color: theme.palette.text.primary }}
                        itemStyle={{ color: theme.palette.text.primary }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};
