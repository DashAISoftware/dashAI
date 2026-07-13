import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

function ResultsGraphsParameters({
  currentMetrics,
  selectedMetrics,
  handleToggleMetric,
  handleSelectAll,
  handleClearAll,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);

  return (
    <Box
      display="flex"
      alignItems="center"
      flexWrap="wrap"
      sx={{
        width: "100%",
        px: 4,
        py: 3,
        gap: 4,
        bgcolor: theme.palette.ui.panelLight,
        borderBottom: `1px solid ${theme.palette.ui.border}`,
      }}
    >
      <Box display="flex" alignItems="center" gap={1} flexShrink={0}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontWeight: 600, letterSpacing: 0.5 }}
        >
          {t("common:metrics", "Metrics")}
        </Typography>

        <Button
          size="small"
          onClick={handleSelectAll}
          disabled={currentMetrics.length === 0}
          sx={{
            minWidth: 0,
            px: 3,
            py: 0,
            fontSize: "0.65rem",
            lineHeight: 1.5,
          }}
        >
          {t("common:all", "All")}
        </Button>
        <Button
          size="small"
          onClick={handleClearAll}
          disabled={selectedMetrics.length === 0}
          sx={{
            minWidth: 0,
            px: 3,
            py: 0,
            fontSize: "0.65rem",
            lineHeight: 1.5,
          }}
        >
          {t("common:none", "None")}
        </Button>
      </Box>

      {currentMetrics.length === 0 ? (
        <Typography variant="caption" color="text.disabled">
          {t("models:label.noMetricsAvailableForThisView")}
        </Typography>
      ) : (
        <Box display="flex" flexWrap="wrap" alignItems="center">
          {currentMetrics.map((metric) => (
            <FormControlLabel
              key={metric}
              control={
                <Checkbox
                  size="small"
                  checked={selectedMetrics.includes(metric)}
                  onChange={() => handleToggleMetric(metric)}
                />
              }
              label={<Typography variant="body2">{metric}</Typography>}
              sx={{ display: "flex", m: 0, mr: 3 }}
            />
          ))}
        </Box>
      )}
    </Box>
  );
}

ResultsGraphsParameters.propTypes = {
  currentMetrics: PropTypes.array.isRequired,
  selectedMetrics: PropTypes.array.isRequired,
  handleToggleMetric: PropTypes.func.isRequired,
  handleSelectAll: PropTypes.func.isRequired,
  handleClearAll: PropTypes.func.isRequired,
};

export default ResultsGraphsParameters;
