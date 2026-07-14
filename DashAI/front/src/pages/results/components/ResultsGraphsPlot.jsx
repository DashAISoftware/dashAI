import React from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import Plot from "react-plotly.js";
import { useTranslation } from "react-i18next";

function EmptyState({ message }) {
  return (
    <Box
      flex={1}
      display="flex"
      alignItems="center"
      justifyContent="center"
      sx={{
        minHeight: 400,
        border: "1px dashed",
        borderColor: "divider",
        borderRadius: 1,
        m: 4,
      }}
    >
      <Typography color="text.secondary">{message}</Typography>
    </Box>
  );
}

function ResultsGraphsPlot({ chartData, onToggleRun }) {
  const { t } = useTranslation(["models"]);
  const theme = useTheme();
  const bgColor = theme.palette.background.paper;
  const textColor = theme.palette.text.primary;
  const gridColor = theme.palette.divider;

  const panels = chartData.bar ?? [];
  const legend = chartData.legend ?? [];
  const yaxis = chartData.yaxis;
  const heatmapData = chartData.heatmap ?? [];

  if (panels.length === 0 && heatmapData.length === 0) {
    return (
      <EmptyState message={t("models:label.noMetricsAvailableForThisView")} />
    );
  }

  const panelLayout = {
    autosize: true,
    height: 240,
    margin: { l: 110, r: 12, t: 8, b: 32 },
    showlegend: false,
    paper_bgcolor: bgColor,
    plot_bgcolor: bgColor,
    bargap: 0.25,
    font: {
      color: textColor,
      family: theme.typography.fontFamily,
      size: 11,
    },
    xaxis: {
      gridcolor: gridColor,
      zerolinecolor: gridColor,
      tickfont: { color: textColor, size: 10 },
    },
    yaxis: {
      gridcolor: gridColor,
      tickfont: { color: textColor, size: 10 },
      automargin: true,
      tickvals: yaxis?.tickvals,
      ticktext: yaxis?.ticktext,
    },
  };

  return (
    <Box sx={{ p: 4, width: "100%" }}>
      {/* Shared legend — one entry per run, same color in every panel */}
      {legend.length > 1 && (
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 3,
            mb: 4,
            px: 1,
          }}
        >
          {legend.map(({ id, label, color, hidden }) => (
            <Box
              key={id}
              onClick={() => onToggleRun(id)}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                cursor: "pointer",
                opacity: hidden ? 0.4 : 1,
                userSelect: "none",
                "&:hover": { opacity: hidden ? 0.65 : 0.8 },
              }}
            >
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  bgcolor: color,
                  flexShrink: 0,
                  filter: hidden ? "grayscale(1)" : "none",
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {label}
              </Typography>
            </Box>
          ))}
        </Box>
      )}

      <Box
        sx={{
          display: "grid",
          gap: 3,
          gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))",
        }}
      >
        {panels.map((panel) => (
          <Box
            key={panel.metric}
            sx={{
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              p: 2,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{ fontWeight: 600, mb: 1, px: 1 }}
            >
              {panel.title}
            </Typography>
            <Plot
              data={panel.data}
              layout={panelLayout}
              useResizeHandler
              style={{ width: "100%", height: "240px" }}
              config={{ responsive: true, displayModeBar: false }}
            />
          </Box>
        ))}

        {/* Heatmap — spans the full grid width since it needs room for
            every run × metric cell, but still reflows as one grid item */}
        {heatmapData.length > 0 && (
          <Box
            sx={{
              gridColumn: "1 / -1",
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              p: 2,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{ fontWeight: 600, mb: 1, px: 1 }}
            >
              {t("models:label.heatmap")}
            </Typography>
            <Box sx={{ height: 460 }}>
              <Plot
                data={heatmapData}
                layout={{
                  ...(chartData.generalLayout ?? {}),
                  autosize: true,
                  width: undefined,
                }}
                useResizeHandler
                style={{ width: "100%", height: "100%" }}
                config={{
                  responsive: true,
                  displayModeBar: false,
                  staticPlot: true,
                }}
              />
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
}

ResultsGraphsPlot.propTypes = {
  chartData: PropTypes.object.isRequired,
  onToggleRun: PropTypes.func.isRequired,
};

export default ResultsGraphsPlot;
