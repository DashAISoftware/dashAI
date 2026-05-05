import React from "react";
import { Box, Divider, Paper, Typography, Tooltip } from "@mui/material";
import { useTranslation } from "react-i18next";

export default function MetricsCard({ title, metrics }) {
  const { t } = useTranslation(["models"]);

  return (
    <Paper elevation={2} sx={{ p: 2, height: "100%" }}>
      <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
        {title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      {metrics && Object.keys(metrics).length > 0 ? (
        Object.entries(metrics).map(([key, metricData]) => {
          // Handle both old format (direct number) and new format (object with value and std_value)
          const value = metricData?.value ?? metricData;
          const stdValue = metricData?.std_value;

          const formattedValue = Number(value).toFixed(4);
          const formattedStd =
            stdValue !== null && stdValue !== undefined
              ? `±${Number(stdValue).toFixed(4)}`
              : null;

          const tooltipTitle = formattedStd
            ? `${formattedValue} ${formattedStd}`
            : formattedValue;

          return (
            <Tooltip key={key} title={tooltipTitle} placement="top" arrow>
              <Box
                sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
              >
                <Typography variant="body2" color="text.secondary">
                  {key}:
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-end",
                  }}
                >
                  <Typography variant="body2" fontWeight="medium">
                    {formattedValue}
                  </Typography>
                  {formattedStd && (
                    <Typography variant="caption" color="text.secondary">
                      {formattedStd}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Tooltip>
          );
        })
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t("models:label.noMetricsAvailable")}
        </Typography>
      )}
    </Paper>
  );
}
