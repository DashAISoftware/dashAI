import React from "react";
import PropTypes from "prop-types";
import { Box, Typography, Tab, Tooltip, Chip } from "@mui/material";
import { useTranslation } from "react-i18next";
import PillTabs from "../../shared/PillTabs";

/**
 * Tab identity for the reports tab, shared by the tab bar, the results
 * body and the right sidebar so the three cannot drift apart.
 *
 * Values 0 to 3 are the live metrics, explainability, predictions and
 * hyperparameter tabs; 4 is left free so tabs added on other branches do not
 * collide with this one.
 */
export const REPORTS_TAB = 5;

const groupLabelSx = {
  textTransform: "uppercase",
  letterSpacing: 0.5,
  fontWeight: 600,
  pl: 2,
  pt: 1,
};

/**
 * The two grouped pill tab bars (Metrics: Live/Hyperparameters, Operations:
 * Explainability/Predictions/Reports) shown above a run's results, with a
 * vertical rule between the groups. Purely presentational.
 */
export default function ResultsTabsHeader({
  activeTab,
  onTabChange,
  isFinished,
  optimizables,
  explainerCount,
  predictionCount,
  reportCount = 0,
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

  return (
    <Box sx={{ display: "flex", alignItems: "flex-end" }}>
      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <Typography variant="caption" color="text.secondary" sx={groupLabelSx}>
          {t("models:label.metrics")}
        </Typography>
        <PillTabs
          value={[0, 3].includes(activeTab) ? activeTab : false}
          onChange={(e, newValue) => onTabChange(newValue)}
          aria-label="Result characteristics tabs"
        >
          <Tab value={0} label={t("models:label.liveMetrics")} />
          <Tab
            value={3}
            label={
              <Tooltip title={hyperparametersTooltip}>
                <span style={{ pointerEvents: "auto" }}>
                  {t("models:label.hyperparameters")}
                </span>
              </Tooltip>
            }
            disabled={!isFinished || optimizables === 0}
          />
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
          value={[1, 2, REPORTS_TAB].includes(activeTab) ? activeTab : false}
          onChange={(e, newValue) => onTabChange(newValue)}
          aria-label="Result operations tabs"
        >
          <Tab
            value={1}
            label={
              <Tooltip title={notFinishedTooltip}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    pointerEvents: "auto",
                  }}
                >
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
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    pointerEvents: "auto",
                  }}
                >
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
          <Tab
            value={REPORTS_TAB}
            label={
              <Tooltip title={notFinishedTooltip}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    pointerEvents: "auto",
                  }}
                >
                  <span>{t("models:label.reports")}</span>
                  {isFinished && (
                    <Chip label={reportCount} size="small" color="primary" />
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
  reportCount: PropTypes.number,
};
