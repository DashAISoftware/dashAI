import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import { Alert, Box, CircularProgress, ToggleButton } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getRunForecasts } from "../../api/run";
import { getApiErrorMessage } from "../../utils/apiError";
import { getTraceColors } from "../../utils/chartColors";
import PillToggleButtonGroup from "../shared/PillToggleButtonGroup";

/**
 * The forecasts a finished backtest run saved (GET /run/{id}/forecasts),
 * origin by origin: the actual values of the window each origin forecast,
 * the forecast, and its intervals by level, against the date.
 *
 * Shown for a strategy whose `result_views` declares "forecasts". Everything
 * drawn comes in the file as it is; nothing is computed on the values.
 */
export default function ForecastsChart({ run }) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);
  const [forecasts, setForecasts] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setForecasts(null);
    setError(null);
    getRunForecasts(run.id)
      .then((data) => {
        if (!cancelled) {
          setForecasts(data);
          setSelected(0);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(getApiErrorMessage(err, t("common:unknownError")));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [run.id]);

  // An origin is named by its partition, numbered when the partition has
  // more than one.
  const originLabels = useMemo(() => {
    const origins = forecasts?.origins ?? [];
    const count = (partition) =>
      origins.filter((origin) => origin.partition === partition).length;
    return origins.map((origin) => {
      const partition = t(`common:${origin.partition}`);
      return count(origin.partition) > 1
        ? `${partition} ${origin.index + 1}`
        : partition;
    });
  }, [forecasts, t]);

  const data = useMemo(() => {
    const origin = forecasts?.origins?.[selected];
    if (!origin) return [];
    const [actualColor, forecastColor] = getTraceColors(theme);
    // Widest band first, so a narrower one is drawn over it.
    const levels = [...(forecasts.levels ?? [])].sort((a, b) => b - a);
    const bands = levels.flatMap((level, position) => {
      const name = t("models:label.predictionInterval", { level });
      const fill = alpha(forecastColor, 0.15 + 0.1 * position);
      const lower = origin.lower?.[String(level)];
      const upper = origin.upper?.[String(level)];
      if (!lower || !upper) return [];
      return [
        {
          type: "scatter",
          mode: "lines",
          name,
          x: origin.dates,
          y: upper,
          line: { width: 0 },
          showlegend: false,
          hoverinfo: "skip",
        },
        {
          type: "scatter",
          mode: "lines",
          name,
          x: origin.dates,
          y: lower,
          line: { width: 0 },
          fill: "tonexty",
          fillcolor: fill,
        },
      ];
    });
    return [
      ...bands,
      {
        type: "scatter",
        mode: "lines+markers",
        name: t("models:label.actual"),
        x: origin.dates,
        y: origin.actual,
        line: { color: actualColor },
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: t("models:label.forecast"),
        x: origin.dates,
        y: origin.forecast,
        line: { color: forecastColor, dash: "dash" },
      },
    ];
  }, [forecasts, selected, theme, t]);

  if (error) {
    return <Alert severity="info">{error}</Alert>;
  }
  if (!forecasts) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {originLabels.length > 1 && (
        <PillToggleButtonGroup
          value={selected}
          onChange={(_, value) => value !== null && setSelected(value)}
        >
          {originLabels.map((label, position) => (
            <ToggleButton key={label} value={position} sx={{ px: 1.5 }}>
              {label}
            </ToggleButton>
          ))}
        </PillToggleButtonGroup>
      )}
      <Plot
        data={data}
        layout={{
          autosize: true,
          height: 380,
          margin: { l: 50, r: 20, t: 20, b: 40 },
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { color: theme.palette.text.primary },
          xaxis: { type: "date" },
          legend: { orientation: "h" },
        }}
        config={{ displaylogo: false, responsive: true }}
        useResizeHandler
        style={{ width: "100%" }}
      />
    </Box>
  );
}

ForecastsChart.propTypes = {
  run: PropTypes.shape({ id: PropTypes.number.isRequired }).isRequired,
};
