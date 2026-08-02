import React from "react";
import PropTypes from "prop-types";
import { Box, Typography, Tab, Tooltip, Chip } from "@mui/material";
import { useTranslation } from "react-i18next";
import PillTabs from "../../shared/PillTabs";
import { useModels } from "../ModelsContext";

const groupLabelSx = {
  textTransform: "uppercase",
  letterSpacing: 0.5,
  fontWeight: 600,
  pl: 2,
  pt: 1,
};

// Matches the MUI small Chip's height, so tabs with a count chip don't grow
// taller than plain-text tabs and push their label off-center.
const TAB_LABEL_HEIGHT = 24;
const tabLabelRowSx = {
  display: "flex",
  alignItems: "center",
  gap: 2,
  height: TAB_LABEL_HEIGHT,
};

/**
 * The two grouped pill tab bars (Metrics: Live/Hyperparameters, Operations:
 * Explainability/Predictions) shown above a run's results, with a vertical
 * rule between the groups. Purely presentational.
 */
export default function ResultsTabsHeader({
  activeTab,
  onTabChange,
  isFinished,
  optimizables,
  explainerCount,
  predictionCount,
}) {
  const { t } = useTranslation(["models"]);

  // Explains *why* a tab is disabled, so it reads as a real (if currently
  // unavailable) tab rather than being confused with the static group labels.
  const notFinishedTooltip = !isFinished
    ? t("models:message.tabAvailableAfterFinish")
    : "";
  const hyperparametersTooltip = !isFinished
    ? notFinishedTooltip
    : optimizables === 0
      ? t("models:message.noOptimizableParamsForHpo")
      : "";

  // Get session from context to check if the evaluation strategy is Cross Validation
  const { selectedSession } = useModels();
  const isCrossValidation =
    selectedSession?.evaluation_strategy ===
    "CrossValidationEvaluationStrategy";

  return (
    <Box sx={{ display: "flex", alignItems: "flex-end" }}>
      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <Typography variant="caption" color="text.secondary" sx={groupLabelSx}>
          {t("models:label.metrics")}
        </Typography>
        <PillTabs
          value={[0, 3, 4].includes(activeTab) ? activeTab : false}
          onChange={(e, newValue) => onTabChange(newValue)}
          aria-label="Result characteristics tabs"
        >
          <Tab
            value={0}
            label={
              <Box sx={tabLabelRowSx}>{t("models:label.liveMetrics")}</Box>
            }
          />
          <Tab
            value={3}
            label={
              <Tooltip title={hyperparametersTooltip}>
                <Box sx={{ ...tabLabelRowSx, pointerEvents: "auto" }}>
                  {t("models:label.hyperparameters")}
                </Box>
              </Tooltip>
            }
            disabled={!isFinished || optimizables === 0}
          />
          {isCrossValidation && (
            <Tab
              value={4}
              label={
                <Box sx={tabLabelRowSx}>{t("models:label.foldGraphs")}</Box>
              }
              disabled={!isFinished}
            />
          )}
        </PillTabs>
      </Box>

      {/* Empty spacer just for the horizontal gap between groups. Kept out of
          the flex height/alignment calculation so the actual rule (positioned
          absolutely inside it) can be sized freely without pushing the tabs
          around. */}
      <Box sx={{ position: "relative", alignSelf: "stretch", width: 0, mx: 4 }}>
        <Box
          sx={{
            position: "absolute",
            top: 32,
            bottom: -16,
            left: 0,
            width: "1px",
            bgcolor: "divider",
          }}
        />
      </Box>

      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <Typography variant="caption" color="text.secondary" sx={groupLabelSx}>
          {t("models:label.operations")}
        </Typography>
        <PillTabs
          value={[1, 2].includes(activeTab) ? activeTab : false}
          onChange={(e, newValue) => onTabChange(newValue)}
          aria-label="Result operations tabs"
        >
          <Tab
            value={1}
            label={
              <Tooltip title={notFinishedTooltip}>
                <Box sx={{ ...tabLabelRowSx, pointerEvents: "auto" }}>
                  <span>{t("models:label.explainability")}</span>
                  {isFinished && (
                    <Chip label={explainerCount} size="small" color="primary" />
                  )}
                </Box>
              </Tooltip>
            }
            disabled={!isFinished}
          />
          <Tab
            value={2}
            label={
              <Tooltip title={notFinishedTooltip}>
                <Box sx={{ ...tabLabelRowSx, pointerEvents: "auto" }}>
                  <span>{t("models:label.predictions")}</span>
                  {isFinished && (
                    <Chip
                      label={predictionCount}
                      size="small"
                      color="primary"
                    />
                  )}
                </Box>
              </Tooltip>
            }
            disabled={!isFinished}
          />
        </PillTabs>
      </Box>
    </Box>
  );
}

ResultsTabsHeader.propTypes = {
  activeTab: PropTypes.number.isRequired,
  onTabChange: PropTypes.func.isRequired,
  isFinished: PropTypes.bool,
  optimizables: PropTypes.number,
  explainerCount: PropTypes.number,
  predictionCount: PropTypes.number,
};
