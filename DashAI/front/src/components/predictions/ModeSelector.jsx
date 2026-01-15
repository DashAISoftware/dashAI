import { useState } from "react";
import { Box, Card, CardContent, Typography, Paper } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import CreateIcon from "@mui/icons-material/Create";
import { useTranslation } from "react-i18next";

function ModeSelector({ predictionMode, setPredictionMode }) {
  const { t } = useTranslation(["prediction"]);

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
        {t("prediction:label.selectPredictionMode")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("prediction:label.chooseInputMethod")}
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
        <Paper
          elevation={predictionMode === "dataset" ? 3 : 0}
          sx={{
            p: 2,
            cursor: "pointer",
            border: 2,
            borderColor:
              predictionMode === "dataset" ? "primary.main" : "divider",
            bgcolor:
              predictionMode === "dataset"
                ? "primary.light"
                : "background.paper",
            "&:hover": {
              bgcolor:
                predictionMode === "dataset" ? "primary.light" : "action.hover",
            },
          }}
          onClick={() => setPredictionMode("dataset")}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <StorageIcon
              color={predictionMode === "dataset" ? "primary" : "action"}
            />
            <Box>
              <Typography variant="body2" fontWeight={600}>
                {t("prediction:label.useExistingDataset")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("prediction:label.selectDatasetFromPlatform")}
              </Typography>
            </Box>
          </Box>
        </Paper>
        <Paper
          elevation={predictionMode === "manual" ? 3 : 0}
          sx={{
            p: 2,
            cursor: "pointer",
            border: 2,
            borderColor:
              predictionMode === "manual" ? "primary.main" : "divider",
            bgcolor:
              predictionMode === "manual"
                ? "primary.light"
                : "background.paper",
            "&:hover": {
              bgcolor:
                predictionMode === "manual" ? "primary.light" : "action.hover",
            },
          }}
          onClick={() => setPredictionMode("manual")}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <CreateIcon
              color={predictionMode === "manual" ? "primary" : "action"}
            />
            <Box>
              <Typography variant="body2" fontWeight={600}>
                {t("prediction:label.manualPrediction")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("prediction:label.enterValuesManually")}
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}

export default ModeSelector;
