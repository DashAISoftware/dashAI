import React from "react";
import { Box, Divider, Paper, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function MetricsCard({ title, metrics }) {
  const { t } = useTranslation(["models"]);

  return (
    <Paper elevation={2} sx={{ p: 4, height: "100%" }}>
      <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
        {title}
      </Typography>
      <Divider sx={{ mb: 4 }} />
      {metrics && Object.keys(metrics).length > 0 ? (
        Object.entries(metrics).map(([key, value]) => (
          <Box
            key={key}
            sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}
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
