import React from "react";
import { Box, Typography, Card, CardContent } from "@mui/material";
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

  return (
    <Box display="flex" flexDirection="column" gap={4}>
      {Object.entries(categoricalStats).map(([column, stats]) => (
        <Card key={column} sx={{ borderRadius: 2 }}>
          <CardContent sx={{ bgcolor: "#2C2C2C" }}>
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
                          backgroundColor: "#121212",
                          borderRadius: 4,
                          color: "#ffffff",
                        }}
                        labelStyle={{ color: "#ffffff" }}
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
                            key={index}
                            fill={
                              [
                                "#8b5cf6",
                                "#a78bfa",
                                "#c4b5fd",
                                "#ddd6fe",
                                "#ede9fe",
                              ][index]
                            }
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#121212",
                          borderRadius: 4,
                        }}
                        labelStyle={{ color: "#ffffff" }}
                        itemStyle={{ color: "#ffffff" }}
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
