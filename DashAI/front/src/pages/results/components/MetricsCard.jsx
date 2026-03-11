import React from "react";
import { Box, Divider, Paper, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { getNumericMetricEntries } from "../../../utils/metricUtils";

export default function MetricsCard({ title, metrics }) {
  const { t } = useTranslation(["models"]);
  const numericMetrics = getNumericMetricEntries(metrics);

  return (
    <Paper elevation={2} sx={{ p: 2, height: "100%" }}>
      <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
        {title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      {numericMetrics.length > 0 ? (
        numericMetrics.map(([key, value]) => (
          <Box
            key={key}
            sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
          >
            <Typography variant="body2" color="text.secondary">
              {key}:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {value.toFixed(4)}
            </Typography>
          </Box>
        ))
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t("models:label.noMetricsAvailable")}
        </Typography>
      )}
    </Paper>
  );
}
