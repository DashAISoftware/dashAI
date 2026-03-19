import React, { Suspense } from "react";
import { Box, CircularProgress, Typography, CardContent, Card } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  LazyBarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "../../../shared/LazyRecharts";
import { useTranslation } from "react-i18next";

const CorrelationsTab = ({ correlations }) => {
  const { t } = useTranslation(["datasets"]);

  const theme = useTheme();
  const corrData = [];
  Object.entries(correlations).forEach(([col1, corrs]) => {
    Object.entries(corrs).forEach(([col2, value]) => {
      if (col1 < col2) {
        // Avoid duplicates
        corrData.push({
          pair: `${col1} - ${col2}`,
          correlation: value,
        });
      }
    });
  });

  corrData.sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation));

  return (
    <Card>
      <CardContent sx={{ bgcolor: theme.palette.ui.panelDark }}>
        <Typography variant="h6" fontWeight="bold" mb={3}>
          {t("datasets:label.correlationAnalysis")}
        </Typography>

        <Box mb={4}>
          <Suspense fallback={<CircularProgress size={24} />}>
            <ResponsiveContainer width="100%" height={300}>
              <LazyBarChart data={corrData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="pair" angle={-45} textAnchor="end" height={100} />
                <YAxis domain={[-1, 1]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    borderRadius: 4,
                    color: theme.palette.text.primary,
                  }}
                  labelStyle={{ color: theme.palette.text.primary }}
                />
                <Bar
                  dataKey="correlation"
                  name={t("datasets:label.correlation")}
                  fill={theme.palette.info.main}
                >
                  {corrData.map((entry) => (
                    <Cell
                      key={entry.pair}
                      fill={
                        entry.correlation > 0
                          ? theme.palette.success.main
                          : theme.palette.error.main
                      }
                    />
                  ))}
                </Bar>
              </LazyBarChart>
            </ResponsiveContainer>
          </Suspense>
        </Box>

        <Box>
          <Typography variant="h6" fontWeight="bold" mb={2}>
            {t("datasets:label.strongCorrelations")} (|r| &gt; 0.5)
          </Typography>
          <Box display="flex" flexDirection="column" gap={1}>
            {corrData
              .filter((d) => Math.abs(d.correlation) > 0.5)
              .map((d) => (
                <Box
                  key={d.pair}
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                  p={2}
                  sx={{
                    backgroundColor: theme.palette.ui.panelMedium,
                    borderRadius: 2,
                  }}
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
