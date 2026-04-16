import { useCallback, useMemo } from "react";
import { Box, Typography, Chip } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import { useTranslation } from "react-i18next";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";

// Tab indices matching DatasetVisualization tab order
const TAB_NUMERIC = 1;
const TAB_TEXT = 3;

/**
 * Collects all column-level observations from dataset info and displays them
 * in the right panel sidebar. Cards are clickable and navigate to the
 * corresponding column card in the appropriate tab.
 */
export default function ColumnInsights({
  numericStats,
  textStats,
  onNavigateTab,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["datasets"]);
  const context = useDatasetsAndNotebooks();
  const setDatasetTab = onNavigateTab ?? context?.setDatasetTab ?? (() => {});

  const insights = useMemo(() => {
    const items = [];

    // Skewed numeric columns (matches Alert in NumericTab)
    if (numericStats) {
      Object.entries(numericStats).forEach(([column, stats]) => {
        if (stats.skew > 1) {
          items.push({
            column,
            tab: TAB_NUMERIC,
            tag: t("datasets:label.insightTagDistribution"),
            color: "warning",
            message: t("datasets:label.insightSkewed", {
              value: stats.skew.toFixed(2),
            }),
          });
        }
      });
    }

    // Low uniqueness text columns (matches Alert in TextTab)
    if (textStats) {
      Object.entries(textStats).forEach(([column, stats]) => {
        if (stats.unique_ratio && stats.unique_ratio * 100 <= 30) {
          items.push({
            column,
            tab: TAB_TEXT,
            tag: t("datasets:label.insightTagTypeSuggestion"),
            color: "warning",
            message: t("datasets:label.insightLowUniqueness", {
              value: (stats.unique_ratio * 100).toFixed(1),
            }),
          });
        }
      });
    }

    return items;
  }, [numericStats, textStats, t]);

  const handleClick = useCallback(
    (insight) => {
      setDatasetTab(insight.tab);
      // Wait for the tab content to render, then scroll to the card
      setTimeout(() => {
        const card = document.querySelector(
          `[data-column-card="${insight.column}"]`,
        );
        if (card) {
          card.scrollIntoView({ behavior: "smooth", block: "center" });
          // Brief highlight effect
          card.style.transition = "box-shadow 0.3s";
          card.style.boxShadow = `0 0 0 2px ${theme.palette.warning.main}`;
          setTimeout(() => {
            card.style.boxShadow = "";
          }, 2000);
        }
      }, 100);
    },
    [setDatasetTab, theme],
  );

  const colorMap = {
    warning: theme.palette.warning,
    info: theme.palette.info,
    error: theme.palette.error,
  };

  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 2,
          py: 1.5,
        }}
      >
        <LightbulbOutlinedIcon
          fontSize="small"
          sx={{ color: theme.palette.warning.main }}
        />
        <Typography variant="subtitle2" fontWeight="bold">
          {t("datasets:label.columnInsights")}
        </Typography>
        <Chip
          label={insights.length}
          size="small"
          color="warning"
          sx={{ height: 22, minWidth: 22, fontWeight: "bold" }}
        />
      </Box>

      {insights.length === 0 ? (
        <Box sx={{ px: 2, pb: 2 }}>
          <Typography variant="caption" color="text.secondary">
            {t("datasets:label.insightEmptyMessage")}
          </Typography>
        </Box>
      ) : (
        /* Insights list */
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
            px: 2,
            pb: 2,
          }}
        >
          {insights.map((insight, index) => {
            const palette = colorMap[insight.color] || theme.palette.info;
            return (
              <Box
                key={`${insight.column}-${insight.tag}-${index}`}
                onClick={() => handleClick(insight)}
                sx={{
                  p: 1.5,
                  borderRadius: 1.5,
                  bgcolor: `${palette.main}15`,
                  border: `1px solid ${palette.main}30`,
                  cursor: "pointer",
                  transition: "all 0.2s",
                  "&:hover": {
                    bgcolor: `${palette.main}25`,
                    transform: "translateX(-2px)",
                  },
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: 1,
                    mb: 0.5,
                  }}
                >
                  <Typography
                    variant="body2"
                    fontWeight="bold"
                    sx={{ color: palette.main }}
                  >
                    {insight.column}
                  </Typography>
                  <Chip
                    label={insight.tag}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: "0.7rem",
                      fontWeight: "bold",
                      bgcolor: `${palette.main}25`,
                      color: palette.main,
                      border: `1px solid ${palette.main}50`,
                    }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {insight.message}
                </Typography>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
