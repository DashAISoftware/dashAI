import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

function ResultsGraphsParameters({
  selectedSplit,
  handleChangeSplit,
  availableMetrics,
  selectedMetrics,
  handleToggleMetric,
  handleSelectAll,
  handleClearAll,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);

  const splits = [
    { key: "train", label: t("common:train") },
    { key: "validation", label: t("common:validation") },
    { key: "test", label: t("common:test") },
  ];

  const currentMetrics = availableMetrics[selectedSplit] ?? [];

  return (
    <Box
      display="flex"
      flexDirection="column"
      sx={{
        width: 220,
        minWidth: 180,
        flexShrink: 0,
        bgcolor: theme.palette.ui.panelLight,
        borderRight: `1px solid ${theme.palette.ui.border}`,
      }}
    >
      {/* ── Split selector ── */}
      <Box
        sx={{
          p: 1.5,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
        }}
      >
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: "block",
            mb: 0.75,
            fontWeight: 600,
            letterSpacing: 0.5,
          }}
        >
          {t("common:split", "Split")}
        </Typography>
        <ToggleButtonGroup
          exclusive
          value={selectedSplit}
          onChange={(_, v) => {
            if (v) handleChangeSplit(v);
          }}
          size="small"
          fullWidth
        >
          {splits.map(({ key, label }) => (
            <ToggleButton
              key={key}
              value={key}
              disabled={availableMetrics[key].length === 0}
              sx={{ flex: 1, py: 0.5, fontSize: "0.7rem" }}
            >
              {label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      {/* ── Metric checkboxes ── */}
      <Box sx={{ p: 1.5, flex: 1, overflowY: "auto" }}>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={0.5}
        >
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontWeight: 600, letterSpacing: 0.5 }}
          >
            {t("common:metrics", "Metrics")}
          </Typography>

          <Box>
            <Button
              size="small"
              onClick={handleSelectAll}
              disabled={currentMetrics.length === 0}
              sx={{
                minWidth: 0,
                px: 0.75,
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
                px: 0.75,
                py: 0,
                fontSize: "0.65rem",
                lineHeight: 1.5,
              }}
            >
              {t("common:none", "None")}
            </Button>
          </Box>
        </Box>

        {currentMetrics.length === 0 ? (
          <Typography variant="caption" color="text.disabled">
            {t("models:label.noMetricsAvailableForThisView")}
          </Typography>
        ) : (
          currentMetrics.map((metric) => (
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
              sx={{ display: "flex", m: 0, py: 0.25 }}
            />
          ))
        )}
      </Box>
    </Box>
  );
}

ResultsGraphsParameters.propTypes = {
  selectedSplit: PropTypes.string.isRequired,
  handleChangeSplit: PropTypes.func.isRequired,
  availableMetrics: PropTypes.shape({
    train: PropTypes.array,
    validation: PropTypes.array,
    test: PropTypes.array,
  }).isRequired,
  selectedMetrics: PropTypes.array.isRequired,
  handleToggleMetric: PropTypes.func.isRequired,
  handleSelectAll: PropTypes.func.isRequired,
  handleClearAll: PropTypes.func.isRequired,
};

export default ResultsGraphsParameters;
