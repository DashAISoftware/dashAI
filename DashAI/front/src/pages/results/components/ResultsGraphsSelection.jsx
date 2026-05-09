import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

function ResultsGraphsSelection({ selectedChart, handleChangeChart, isCv }) {
  const { t } = useTranslation(["models"]);
  const theme = useTheme();

  return (
    <Box
      display="flex"
      alignItems="center"
      gap={2}
      px={2}
      py={1}
      sx={{ borderBottom: `1px solid ${theme.palette.ui.border}` }}
    >
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ fontWeight: 600, letterSpacing: 0.5 }}
      >
        {t("models:label.chartType", "Chart type")}
      </Typography>

      <ToggleButtonGroup
        exclusive
        value={selectedChart}
        onChange={(_, v) => {
          if (v) handleChangeChart(v);
        }}
        size="small"
      >
        <ToggleButton value="bar">{t("models:label.bar")}</ToggleButton>
        <ToggleButton value="heatmap">{t("models:label.heatmap")}</ToggleButton>
        {isCv && (
          <ToggleButton
            value="fold_metrics"
            title="Cross-Validation Fold Metrics"
          >
            Fold Metrics
          </ToggleButton>
        )}
      </ToggleButtonGroup>
    </Box>
  );
}

ResultsGraphsSelection.propTypes = {
  selectedChart: PropTypes.string.isRequired,
  handleChangeChart: PropTypes.func.isRequired,
  isCv: PropTypes.bool,
};

export default ResultsGraphsSelection;
