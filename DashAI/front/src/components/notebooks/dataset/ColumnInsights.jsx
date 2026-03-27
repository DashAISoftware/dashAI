import React, { useMemo, useState } from "react";
import { Box, Typography, Chip, Collapse, IconButton } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { useTranslation } from "react-i18next";

/**
 * Collects all column-level observations from dataset info and displays them
 * in a collapsible sidebar panel, grouped by column.
 */
export default function ColumnInsights({ numericStats, textStats }) {
  const theme = useTheme();
  const { t } = useTranslation(["datasets"]);
  const [expanded, setExpanded] = useState(true);

  const insights = useMemo(() => {
    const items = [];

    // Skewed numeric columns (matches Alert in NumericTab)
    if (numericStats) {
      Object.entries(numericStats).forEach(([column, stats]) => {
        if (stats.skew > 1) {
          items.push({
            column,
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

  if (insights.length === 0) return null;

  const colorMap = {
    warning: theme.palette.warning,
    info: theme.palette.info,
    error: theme.palette.error,
  };

  return (
    <Box
      sx={{
        bgcolor: theme.palette.ui.panelDark,
        borderRadius: 2,
        border: `1px solid ${theme.palette.ui.border}`,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 1.5,
          cursor: "pointer",
          "&:hover": { bgcolor: theme.palette.ui.hover },
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
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
        <IconButton size="small">
          {expanded ? (
            <ExpandLessIcon fontSize="small" />
          ) : (
            <ExpandMoreIcon fontSize="small" />
          )}
        </IconButton>
      </Box>

      {/* Insights list */}
      <Collapse in={expanded}>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
            p: 2,
            pt: 0,
          }}
        >
          {insights.map((insight, index) => {
            const palette = colorMap[insight.color] || theme.palette.info;
            return (
              <Box
                key={`${insight.column}-${insight.tag}-${index}`}
                sx={{
                  p: 1.5,
                  borderRadius: 1.5,
                  border: `1px solid ${palette.dark}30`,
                  borderLeft: `3px solid ${palette.main}`,
                  bgcolor: theme.palette.ui.box,
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
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
                      bgcolor: `${palette.main}20`,
                      color: palette.main,
                      border: `1px solid ${palette.main}40`,
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
      </Collapse>
    </Box>
  );
}
