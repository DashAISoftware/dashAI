import React from "react";
import { Box, Typography, CardContent, Card } from "@mui/material";
import { useTheme } from "@mui/material/styles";
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

const CorrelationsTab = ({ correlations }) => {
  const theme = useTheme();
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
      <CardContent sx={{ bgcolor: theme.palette.ui.panelDark }}>
        <Typography variant="h6" fontWeight="bold" mb={3}>
          Correlation Analysis
        </Typography>

        <Box mb={4}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={corrData}>
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
              <Bar dataKey="correlation" fill={theme.palette.info.main}>
                {corrData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={
                      entry.correlation > 0
                        ? theme.palette.success.main
                        : theme.palette.error.main
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>

        <Box>
          <Typography variant="h6" fontWeight="bold" mb={2}>
            Strong Correlations (|r| &gt; 0.5)
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
                  No strong correlations detected
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
