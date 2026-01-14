import React from "react";
import { Box, Typography, CardContent, Card } from "@mui/material";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useTranslation } from "react-i18next";

const CorrelationsTab = ({ correlations }) => {
  const { t } = useTranslation(["datasets"]);

  const corrData = [];
  Object.entries(correlations).forEach(([col1, corrs]) => {
    Object.entries(corrs).forEach(([col2, value]) => {
      if (col1 < col2) {
        // Avoid duplicates
        corrData.push({ pair: `${col1} - ${col2}`, correlation: value });
      }
    });
  });

  corrData.sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation));

  return (
    <Card>
      <CardContent sx={{ bgcolor: "#2C2C2C" }}>
        <Typography variant="h6" fontWeight="bold" mb={3}>
          {t("datasets:label.correlationAnalysis")}
        </Typography>

        <Box mb={4}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={corrData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="pair" angle={-45} textAnchor="end" height={100} />
              <YAxis domain={[-1, 1]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#121212",
                  borderRadius: 4,
                  color: "#ffffff",
                }}
                labelStyle={{ color: "#ffffff" }}
              />
              <Bar dataKey="correlation" fill="#3b82f6">
                {corrData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={entry.correlation > 0 ? "#10b981" : "#ef4444"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>

        <Box>
          <Typography variant="h6" fontWeight="bold" mb={2}>
            {t("datasets:label.strongCorrelations")} (|r| &gt; 0.5)
          </Typography>
          <Box display="flex" flexDirection="column" gap={1}>
            {corrData
              .filter((d) => Math.abs(d.correlation) > 0.5)
              .map((d, idx) => (
                <Box
                  key={idx}
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                  p={2}
                  sx={{ backgroundColor: "#363636", borderRadius: 2 }}
                >
                  <Typography variant="body2" fontWeight={500}>
                    {d.pair}
                  </Typography>
                  <Typography
                    variant="body2"
                    fontWeight="bold"
                    sx={{
                      color: d.correlation > 0 ? "success.main" : "error.main",
                    }}
                  >
                    {d.correlation.toFixed(3)}
                  </Typography>
                </Box>
              ))}
            {corrData.filter((d) => Math.abs(d.correlation) > 0.5).length ===
              0 && (
              <Box p={2}>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  fontStyle="italic"
                >
                  {t("datasets:label.noStrongCorrelationsFound")}
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default CorrelationsTab;
