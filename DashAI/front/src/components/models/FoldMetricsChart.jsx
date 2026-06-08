import React, {
  useEffect,
  useRef,
  useState,
  useMemo,
  useCallback,
} from "react";
import PropTypes from "prop-types";
import Plot from "react-plotly.js";
import {
  Box,
  CircularProgress,
  Alert,
  AlertTitle,
  ToggleButton,
  ToggleButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getFoldMetrics, isRepeatedFoldMetrics } from "../../api/run";
import ResultsGraphsParameters from "../../pages/results/components/ResultsGraphsParameters";
import OuterFoldMetricsTable from "./OuterFoldMetricsTable";

// ─── Pure helpers (defined outside component — stable references) ─────────────

const THEME_COLORS = (theme) => [
  theme.palette.primary.main,
  theme.palette.secondary.main,
  theme.palette.success.main,
  theme.palette.warning.main,
  theme.palette.error.main,
];

const errorInverse = (x) => {
  const a = 0.147;
  const ln = Math.log(1 - x * x);
  const term1 = 2 / (Math.PI * a) + ln / 2;
  const term2 = ln / a;
  return Math.sign(x) * Math.sqrt(Math.sqrt(term1 * term1 - term2) - term1);
};

const calculateNormalQuantiles = (data) => {
  const sorted = [...data].sort((a, b) => a - b);
  return sorted.map((sample, i) => ({
    sample,
    theoretical:
      Math.sqrt(2) * errorInverse(2 * ((i + 0.5) / sorted.length) - 1),
  }));
};

const computeAveraged = (allRepetitionsData) => {
  const reps = Object.keys(allRepetitionsData).filter((k) =>
    k.startsWith("rep_"),
  );
  if (reps.length === 0) return null;
  const metricNames = Object.keys(allRepetitionsData[reps[0]]);
  return Object.fromEntries(
    metricNames.map((metric) => {
      const nFolds = allRepetitionsData[reps[0]][metric].length;
      return [
        metric,
        Array.from({ length: nFolds }, (_, i) => {
          const vals = reps.map(
            (rep) => allRepetitionsData[rep][metric][i] ?? 0,
          );
          return vals.reduce((a, b) => a + b, 0) / vals.length;
        }),
      ];
    }),
  );
};

const computeConcatenated = (allRepetitionsData) => {
  const reps = Object.keys(allRepetitionsData).filter((k) =>
    k.startsWith("rep_"),
  );
  if (reps.length === 0) return null;
  const metricNames = Object.keys(allRepetitionsData[reps[0]]);
  return Object.fromEntries(
    metricNames.map((metric) => [
      metric,
      reps.flatMap((rep) => allRepetitionsData[rep][metric]),
    ]),
  );
};

// ─── Trace builders (pure functions, defined outside component) ───────────────

const buildBoxplotTraces = (foldMetrics, selectedMetrics, colors) =>
  Object.keys(foldMetrics)
    .sort()
    .filter((name) => selectedMetrics.includes(name))
    .map((metricName, index) => ({
      y: foldMetrics[metricName],
      name: metricName,
      type: "box",
      boxmean: "sd",
      marker: { color: colors[index % colors.length] },
      hovertemplate:
        "<b>%{fullData.name}</b><br>Value: %{y:.4f}<extra></extra>",
    }));

const buildLineTraces = (foldMetrics, selectedMetrics, colors) =>
  Object.keys(foldMetrics)
    .sort()
    .filter((name) => selectedMetrics.includes(name))
    .map((metricName, index) => {
      const values = foldMetrics[metricName];
      const color = colors[index % colors.length];
      return {
        x: Array.from({ length: values.length }, (_, i) => i + 1),
        y: values,
        name: metricName,
        type: "scatter",
        mode: "lines+markers",
        line: { color, width: 2 },
        marker: { size: 6, color },
        hovertemplate:
          "<b>%{fullData.name}</b><br>Fold: %{x}<br>Value: %{y:.4f}<extra></extra>",
      };
    });

const buildHistogramTraces = (foldMetrics, selectedMetrics, colors) =>
  Object.keys(foldMetrics)
    .sort()
    .filter((name) => selectedMetrics.includes(name))
    .map((metricName, index) => ({
      x: foldMetrics[metricName],
      name: metricName,
      type: "histogram",
      nbinsx: Math.max(5, Math.ceil(Math.sqrt(foldMetrics[metricName].length))),
      marker: { color: colors[index % colors.length], opacity: 0.7 },
      hovertemplate: "<b>%{fullData.name}</b><br>Count: %{y}<extra></extra>",
    }));

const buildQQTraces = (foldMetrics, selectedMetrics, colors) => {
  const traces = [];
  const allTheoretical = [];

  Object.keys(foldMetrics)
    .sort()
    .filter((name) => selectedMetrics.includes(name))
    .forEach((metricName, index) => {
      const values = foldMetrics[metricName];
      if (values.length < 3) return;
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      const std = Math.sqrt(
        values.reduce((s, v) => s + Math.pow(v - mean, 2), 0) / values.length,
      );
      const quantileData = calculateNormalQuantiles(values);
      const sampleQ = quantileData.map((q) => q.sample);
      const theoreticalQ = quantileData.map((q) => mean + q.theoretical * std);
      allTheoretical.push(...theoreticalQ);
      traces.push({
        x: theoreticalQ,
        y: sampleQ,
        name: metricName,
        type: "scatter",
        mode: "markers",
        marker: { size: 8, color: colors[index % colors.length] },
        hovertemplate:
          "<b>%{fullData.name}</b><br>Theoretical: %{x:.3f}<br>Sample: %{y:.3f}<extra></extra>",
      });
    });

  if (allTheoretical.length > 0) {
    const tMin = Math.min(...allTheoretical);
    const tMax = Math.max(...allTheoretical);
    const pad = (tMax - tMin) * 0.1;
    traces.push({
      x: [tMin - pad, tMax + pad],
      y: [tMin - pad, tMax + pad],
      name: "Reference (Normal)",
      type: "scatter",
      mode: "lines",
      line: { color: "#ff7f0e", dash: "solid", width: 3 },
      hoverinfo: "skip",
      showlegend: true,
    });
  }

  return traces;
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function FoldMetricsChart({ runId, isNestedCV = false }) {
  const theme = useTheme();
  const { t } = useTranslation("models");
  const colors = useMemo(() => THEME_COLORS(theme), [theme]);

  const [allRepetitionsData, setAllRepetitionsData] = useState(null);
  const [selectedRepetition, setSelectedRepetition] = useState(null);
  // Separate "refreshing" from full "loading" — avoids unmounting the chart
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [chartType, setChartType] = useState("boxplot");
  const [foldScope, setFoldScope] = useState("default");
  const [viewMode, setViewMode] = useState("charts");
  const [split, setSplit] = useState("TRAIN");
  const [selectedMetrics, setSelectedMetrics] = useState([]);

  const selectedMetricsRef = useRef([]);
  // Track whether we already have data to decide between full-load and refresh
  const hasDataRef = useRef(false);

  const metricSplit = split === "TRAIN" ? "train" : "test";

  // ── Fetch ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!runId) return;

    // If we already have data (e.g. split change), show a non-blocking overlay
    // instead of unmounting the chart entirely
    if (hasDataRef.current) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    const controller = new AbortController();

    const fetchFoldMetrics = async () => {
      try {
        const scope = isNestedCV && foldScope === "outer" ? "outer" : "default";
        const data = await getFoldMetrics(runId, {
          metricSplit,
          scope,
          signal: controller.signal,
        });

        let nextData;
        let nextRepetition;

        if (isRepeatedFoldMetrics(data)) {
          const repKeys = Object.keys(data)
            .filter((key) => key.startsWith("rep_"))
            .sort(
              (a, b) => parseInt(a.split("_")[1]) - parseInt(b.split("_")[1]),
            );

          nextData = data;
          // Keep current repetition if still valid
          const currentRep = selectedRepetition;
          const isValidRep =
            currentRep === "averaged" || repKeys.includes(currentRep);
          nextRepetition = isValidRep ? currentRep : "averaged";
        } else {
          nextData = { rep_0: data };
          nextRepetition = "rep_0";
        }

        setAllRepetitionsData(nextData);
        setSelectedRepetition(nextRepetition);
        hasDataRef.current = true;
      } catch (err) {
        if (err.name === "CanceledError" || err.name === "AbortError") return;
        setError(err.response?.data?.detail || "Failed to load fold metrics");
        console.error("Error fetching fold metrics:", err);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    };

    fetchFoldMetrics();

    return () => controller.abort();
    // selectedRepetition intentionally excluded — we only read it as "current value at fetch time"
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, metricSplit, foldScope, isNestedCV]);

  // ── Derived data ───────────────────────────────────────────────────────────

  // Single source of truth for current fold data (covers all chart types)
  const currentFoldMetrics = useMemo(() => {
    if (!allRepetitionsData || !selectedRepetition) return null;
    if (selectedRepetition === "averaged")
      return computeAveraged(allRepetitionsData);
    return allRepetitionsData[selectedRepetition] ?? null;
  }, [allRepetitionsData, selectedRepetition]);

  // For QQ: concatenate all reps when "averaged", otherwise same as current
  const qqFoldMetrics = useMemo(() => {
    if (!allRepetitionsData || !selectedRepetition) return null;
    if (selectedRepetition === "averaged")
      return computeConcatenated(allRepetitionsData);
    return allRepetitionsData[selectedRepetition] ?? null;
  }, [allRepetitionsData, selectedRepetition]);

  const availableMetrics = useMemo(
    () => (currentFoldMetrics ? Object.keys(currentFoldMetrics).sort() : []),
    [currentFoldMetrics],
  );

  const availableReps = useMemo(
    () =>
      allRepetitionsData
        ? Object.keys(allRepetitionsData)
            .filter((k) => k.startsWith("rep_"))
            .sort(
              (a, b) => parseInt(a.split("_")[1]) - parseInt(b.split("_")[1]),
            )
        : [],
    [allRepetitionsData],
  );

  // ── Selection reconciliation ───────────────────────────────────────────────
  // Fires when availableMetrics changes (new fetch or rep change).
  // Keeps user selection if any of the chosen metrics still exist; otherwise selects all.
  useEffect(() => {
    if (availableMetrics.length === 0) return;
    const valid = selectedMetricsRef.current.filter((m) =>
      availableMetrics.includes(m),
    );
    const next = valid.length > 0 ? valid : availableMetrics;
    selectedMetricsRef.current = next;
    setSelectedMetrics(next);
  }, [availableMetrics]);

  // ── Metric handlers ────────────────────────────────────────────────────────
  const handleToggleMetric = useCallback(
    (name) => {
      const next = selectedMetrics.includes(name)
        ? selectedMetrics.filter((m) => m !== name)
        : availableMetrics.filter((m) =>
            new Set([...selectedMetrics, name]).has(m),
          );
      selectedMetricsRef.current = next;
      setSelectedMetrics(next);
    },
    [selectedMetrics, availableMetrics],
  );

  const handleSelectAll = useCallback(() => {
    selectedMetricsRef.current = availableMetrics;
    setSelectedMetrics(availableMetrics);
  }, [availableMetrics]);

  const handleClearAll = useCallback(() => {
    selectedMetricsRef.current = [];
    setSelectedMetrics([]);
  }, []);

  // ── Traces ─────────────────────────────────────────────────────────────────
  const traces = useMemo(() => {
    const fm = chartType === "qq" ? qqFoldMetrics : currentFoldMetrics;
    if (!fm) return [];
    switch (chartType) {
      case "line":
        return buildLineTraces(fm, selectedMetrics, colors);
      case "histogram":
        return buildHistogramTraces(fm, selectedMetrics, colors);
      case "qq":
        return buildQQTraces(fm, selectedMetrics, colors);
      default:
        return buildBoxplotTraces(fm, selectedMetrics, colors);
    }
  }, [chartType, currentFoldMetrics, qqFoldMetrics, selectedMetrics, colors]);

  // ── Layout ─────────────────────────────────────────────────────────────────
  const layout = useMemo(() => {
    const { palette, typography } = theme;
    const textColor = palette.text.primary;
    const gridColor = palette.divider;

    const base = {
      paper_bgcolor: palette.background.paper,
      plot_bgcolor: palette.background.default,
      font: {
        color: textColor,
        family: typography.fontFamily,
      },
      hovermode: "closest",
      margin: { l: 40, r: 0, t: 40, b: 40 },
      autosize: true,
      showlegend: false,
      yaxis: {
        title: {
          text: t("models:label.metricValue"),
          font: { color: textColor },
        },
        gridcolor: gridColor,
        titlefont: { color: textColor },
        tickfont: { color: textColor },
      },
    };

    const FormatAxis = (title) => ({
      ...(title ? { title: { text: title, font: { color: textColor } } } : {}),
      gridcolor: gridColor,
      titlefont: { color: textColor },
      tickfont: { color: textColor },
    });

    const titles = {
      boxplot: t("models:label.boxPlot"),
      line: t("models:label.linesPlot"),
      qq: t("models:label.qqPlot"),
      histogram: t("models:label.histogramPlot"),
    };

    const extra = {
      boxplot: { xaxis: FormatAxis() },
      line: { xaxis: FormatAxis(t("models:label.foldNumber")) },
      qq: {
        showlegend: false,
        xaxis: FormatAxis(t("models:label.theoricalQuantiles")),
        yaxis: {
          ...base.yaxis,
          title: {
            text: t("models:label.sampleQuantiles"),
            font: { color: textColor },
          },
        },
      },
      histogram: {
        xaxis: FormatAxis(t("models:label.metricValue")),
        yaxis: {
          ...base.yaxis,
          title: {
            text: t("models:label.frequency"),
            font: { color: textColor },
          },
        },
      },
    };

    return {
      ...base,
      title: { text: titles[chartType], font: { size: 14 } },
      ...extra[chartType],
    };
  }, [theme, chartType, t]);

  // ── Early returns ──────────────────────────────────────────────────────────
  if (!runId) {
    return (
      <Alert severity="info">
        <AlertTitle>No Run Selected</AlertTitle>
        Select a run to view fold-level metrics.
      </Alert>
    );
  }

  if (viewMode === "charts" && loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (viewMode === "charts" && error) {
    return (
      <Alert severity="warning">
        <AlertTitle>No Fold Data Available</AlertTitle>
        {error} — This run may not use cross-validation.
      </Alert>
    );
  }

  if (viewMode === "charts" && (!allRepetitionsData || !selectedRepetition)) {
    return (
      <Alert severity="info">
        <AlertTitle>No Fold Metrics</AlertTitle>
        No fold-level metrics available for this run.
      </Alert>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        minHeight: 400,
      }}
    >
      {isNestedCV && (
        <Box sx={{ px: 1.5, pt: 1 }}>
          <ToggleButtonGroup
            exclusive
            value={viewMode}
            onChange={(_, v) => {
              if (v) setViewMode(v);
            }}
            size="small"
            sx={{ height: 28 }}
          >
            <ToggleButton
              value="charts"
              sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
            >
              {t("models:label.graphs", "Gráficos")}
            </ToggleButton>
            <ToggleButton
              value="nested"
              sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
            >
              Nested CV
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      )}

      {isNestedCV && viewMode === "nested" ? (
        <OuterFoldMetricsTable runId={runId} />
      ) : (
        <>
          {/* Toolbar */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 1.5,
              px: 1.5,
              py: 1,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <ToggleButtonGroup
                exclusive
                value={split}
                onChange={(_, v) => {
                  if (v) setSplit(v);
                }}
                size="small"
                sx={{ height: 28 }}
              >
                <ToggleButton
                  value="TRAIN"
                  sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
                >
                  {t("models:label.train")}
                </ToggleButton>
                <ToggleButton
                  value="TEST"
                  sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
                >
                  {t("models:label.test")}
                </ToggleButton>
              </ToggleButtonGroup>

              {isNestedCV && (
                <ToggleButtonGroup
                  exclusive
                  value={foldScope}
                  onChange={(_, v) => {
                    if (v) setFoldScope(v);
                  }}
                  size="small"
                  sx={{ height: 28 }}
                >
                  <ToggleButton
                    value="outer"
                    title="Outer folds — reliable generalization estimate from nested CV"
                    sx={{ px: 0.75, py: 0, fontSize: "0.75rem" }}
                  >
                    Outer
                  </ToggleButton>
                  <ToggleButton
                    value="default"
                    title="Folds used during final HPO training to produce the model"
                    sx={{ px: 0.75, py: 0, fontSize: "0.75rem" }}
                  >
                    Default
                  </ToggleButton>
                </ToggleButtonGroup>
              )}

              {availableReps.length > 1 && (
                <FormControl sx={{ minWidth: 140 }} size="small">
                  <InputLabel sx={{ fontSize: "0.85rem" }}>
                    {t("models:label.repetition")}
                  </InputLabel>
                  <Select
                    value={selectedRepetition ?? ""}
                    label={t("models:label.repetition")}
                    onChange={(e) => setSelectedRepetition(e.target.value)}
                    sx={{ fontSize: "0.85rem" }}
                  >
                    <MenuItem value="averaged">
                      {chartType === "qq"
                        ? t("models:label.allRepetitions")
                        : t("models:label.averaged")}
                    </MenuItem>
                    {availableReps.map((rep) => (
                      <MenuItem key={rep} value={rep}>
                        {t("models:label.repetition")}{" "}
                        {parseInt(rep.split("_")[1]) + 1}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            </Box>

            <ToggleButtonGroup
              exclusive
              value={chartType}
              onChange={(_, v) => {
                if (v) setChartType(v);
              }}
              size="small"
              sx={{ height: 28 }}
            >
              {[
                {
                  value: "boxplot",
                  label: "Boxplot",
                  title: "Boxplot with statistics",
                },
                {
                  value: "line",
                  label: t("models:label.lines"),
                  title: "Line chart showing fold progression",
                },
                {
                  value: "qq",
                  label: "Q-Q",
                  title: "Q-Q plot for normality assessment",
                },
                {
                  value: "histogram",
                  label: "Hist",
                  title: "Distribution histogram",
                },
              ].map(({ value, label, title }) => (
                <ToggleButton
                  key={value}
                  value={value}
                  title={title}
                  sx={{ px: 1, py: 0, fontSize: "0.75rem" }}
                >
                  {label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          {/* Chart + metrics sidebar — always mounted, overlay during refresh */}
          <Box
            sx={{
              display: "flex",
              flex: 1,
              minHeight: 0,
              width: "100%",
              position: "relative",
            }}
          >
            {refreshing && (
              <Box
                sx={{
                  position: "absolute",
                  inset: 0,
                  zIndex: 10,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  bgcolor: "action.disabledBackground",
                  borderRadius: 1,
                  opacity: 0.6,
                  pointerEvents: "none",
                }}
              >
                <CircularProgress size={28} />
              </Box>
            )}
            <ResultsGraphsParameters
              currentMetrics={availableMetrics}
              selectedMetrics={selectedMetrics}
              handleToggleMetric={handleToggleMetric}
              handleSelectAll={handleSelectAll}
              handleClearAll={handleClearAll}
            />
            <Box sx={{ flex: 1, minHeight: 0, width: "100%", p: 0.5 }}>
              <Plot
                data={traces}
                layout={layout}
                config={{
                  responsive: true,
                  displayModeBar: true,
                  displaylogo: false,
                  modeBarButtonsToRemove: [
                    "select2d",
                    "lasso2d",
                    "zoomIn2d",
                    "autoScale2d",
                  ],
                }}
                style={{ width: "100%", height: "100%" }}
              />
            </Box>
          </Box>
        </>
      )}
    </Box>
  );
}

FoldMetricsChart.propTypes = {
  runId: PropTypes.number,
  isNestedCV: PropTypes.bool,
};
