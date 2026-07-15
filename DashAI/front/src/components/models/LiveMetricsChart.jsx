import {
  Box,
  ToggleButtonGroup,
  ToggleButton,
  Typography,
  Button,
  ButtonGroup,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import Plot from "react-plotly.js";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { getModelSessionById } from "../../api/modelSession";
import ResultsGraphsParameters from "../../pages/results/components/ResultsGraphsParameters";

// Same color source as the session results charts (ResultsGraphsPlot /
// graphsMaking) so a metric's line color stays visually consistent with the
// rest of the app.
const getTraceColors = (theme) => [
  theme.palette.primary.main,
  theme.palette.secondary.main,
  ...(theme.palette.chart?.palette || [
    "#66bb6a",
    "#42a5f5",
    "#ff9800",
    "#ab47bc",
    "#ef5350",
    "#26a69a",
    "#8d6e63",
    "#78909c",
  ]),
];

export function LiveMetricsChart({ run }) {
  const { t } = useTranslation("models");
  const theme = useTheme();
  const [level, setLevel] = useState(null);
  const [split, setSplit] = useState("TRAIN");
  const [data, setData] = useState({});
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [availableMetrics, setAvailableMetrics] = useState({
    TRAIN: [],
    VALIDATION: [],
    TEST: [],
  });

  const selectedMetricsPerSplit = useRef({
    TRAIN: null,
    VALIDATION: null,
    TEST: null,
  });
  const socketRef = useRef(null);

  useEffect(() => {
    if (run.status === 3 && run.test_metrics) {
      setData((prev) => {
        const next = structuredClone(prev);

        const formattedTestMetrics = {};
        for (const metricName in run.test_metrics) {
          const value = run.test_metrics[metricName];
          if (Array.isArray(value)) {
            formattedTestMetrics[metricName] = value;
          } else {
            formattedTestMetrics[metricName] = [
              { step: 1, value: value, timestamp: new Date().toISOString() },
            ];
          }
        }

        next.TEST = {
          TRIAL: formattedTestMetrics,
          STEP: formattedTestMetrics,
          EPOCH: formattedTestMetrics,
        };
        return next;
      });
    }
  }, [run.status, run.test_metrics]);

  useEffect(() => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    // When a new training starts, clear all previous metrics
    const isStarting = run.status === 1 || run.status === 2;
    if (isStarting) {
      setData({});
      setSelectedMetrics([]);
      selectedMetricsPerSplit.current = {
        TRAIN: null,
        VALIDATION: null,
        TEST: null,
      };
    }

    const wsOrigin = new URL(
      process.env.REACT_APP_API_URL || "/",
      window.location.origin,
    ).origin;
    let wsUrl;
    try {
      wsUrl = new URL(`/api/v1/metrics/ws/${run.id}`, wsOrigin);
    } catch (e) {
      console.error("Invalid WebSocket base URL:", wsOrigin, e);
      return;
    }
    if (wsUrl.protocol === "http:") {
      wsUrl.protocol = "ws:";
    } else if (wsUrl.protocol === "https:") {
      wsUrl.protocol = "wss:";
    }
    const ws = new WebSocket(wsUrl.toString());

    ws.onmessage = (event) => {
      const incoming = JSON.parse(event.data);

      setData((prev) => {
        const next = structuredClone(prev);

        for (const splitKey in incoming) {
          if (splitKey === "run_status") continue;
          next[splitKey] ??= {};

          for (const levelKey in incoming[splitKey]) {
            next[splitKey][levelKey] ??= {};

            for (const metricName in incoming[splitKey][levelKey]) {
              const incomingPoints = incoming[splitKey][levelKey][metricName];

              if (!Array.isArray(next[splitKey][levelKey][metricName])) {
                next[splitKey][levelKey][metricName] = [...incomingPoints];
              } else {
                next[splitKey][levelKey][metricName].push(...incomingPoints);
              }
            }
          }
        }

        return next;
      });
    };

    ws.onclose = () => {
      if (run.test_metrics) {
        setData((prev) => {
          // Skip if TEST data already exists to avoid duplicate re-render
          if (prev.TEST && Object.keys(prev.TEST).length > 0) {
            return prev;
          }

          const next = structuredClone(prev);

          const formattedTestMetrics = {};
          for (const metricName in run.test_metrics) {
            const value = run.test_metrics[metricName];
            if (Array.isArray(value)) {
              formattedTestMetrics[metricName] = value;
            } else {
              formattedTestMetrics[metricName] = [
                { step: 1, value: value, timestamp: new Date().toISOString() },
              ];
            }
          }

          next.TEST = {
            TRIAL: formattedTestMetrics,
            STEP: formattedTestMetrics,
            EPOCH: formattedTestMetrics,
          };
          return next;
        });
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socketRef.current = ws;

    return () => {
      try {
        ws.close();
      } catch (e) {
        console.log("WebSocket already closed");
      }
    };
  }, [run.id, run.status]);

  useEffect(() => {
    if (!run.model_session_id) return;

    let mounted = true;

    getModelSessionById(run.model_session_id.toString()).then((session) => {
      if (!mounted) return;

      setAvailableMetrics({
        TRAIN: session.train_metrics ?? [],
        VALIDATION: session.validation_metrics ?? [],
        TEST: session.test_metrics ?? [],
      });
    });

    return () => {
      mounted = false;
    };
  }, [run.model_session_id]);

  const filteredMetrics = useMemo(() => {
    const metrics = data[split]?.[level] ?? {};
    const allowedMetrics = availableMetrics[split] ?? [];
    return Object.fromEntries(
      Object.entries(metrics).filter(([name]) => allowedMetrics.includes(name)),
    );
  }, [data, split, level, availableMetrics]);

  // One small panel per metric — each keeps its own x/y scale instead of
  // sharing a single overlaid axis, same "small multiples" approach used for
  // the session results charts.
  const panels = useMemo(() => {
    const colors = getTraceColors(theme);
    return selectedMetrics.map((metricName, idx) => {
      const points = (filteredMetrics[metricName] ?? [])
        .slice()
        .sort((a, b) => a.step - b.step);
      return {
        metric: metricName,
        x: points.map((p) => p.step),
        y: points.map((p) => p.value),
        color: colors[idx % colors.length],
      };
    });
  }, [selectedMetrics, filteredMetrics, theme]);

  const hasTrialData =
    data[split]?.TRIAL && Object.keys(data[split].TRIAL).length > 0;
  const hasStepData =
    data[split]?.STEP && Object.keys(data[split].STEP).length > 0;
  const hasEpochData =
    data[split]?.EPOCH && Object.keys(data[split].EPOCH).length > 0;

  const levelLabel = useMemo(() => {
    if (!level) return "";
    return t(`models:label.${level.toLowerCase()}`);
  }, [level, t]);

  useEffect(() => {
    const currentLevelHasData =
      (level === "TRIAL" && hasTrialData) ||
      (level === "STEP" && hasStepData) ||
      (level === "EPOCH" && hasEpochData);

    if (currentLevelHasData) {
      return;
    }

    if (hasEpochData) setLevel("EPOCH");
    else if (hasStepData) setLevel("STEP");
    else if (hasTrialData) setLevel("TRIAL");
    else setLevel(null);
  }, [split, hasEpochData, hasStepData, hasTrialData, level]);

  const filteredMetricKeys = useMemo(
    () => Object.keys(filteredMetrics).sort().join(","),
    [filteredMetrics],
  );

  useEffect(() => {
    const metricNames = filteredMetricKeys ? filteredMetricKeys.split(",") : [];

    if (metricNames.length === 0) {
      setSelectedMetrics([]);
      return;
    }

    const savedSelection = selectedMetricsPerSplit.current[split];

    if (savedSelection !== null) {
      const validSavedMetrics = savedSelection.filter((m) =>
        metricNames.includes(m),
      );
      setSelectedMetrics(validSavedMetrics);
    } else {
      setSelectedMetrics(metricNames);
    }
  }, [split, level, filteredMetricKeys]);

  const handleToggleMetric = (metric) => {
    const canonicalOrder = Object.keys(filteredMetrics);
    const newSelection = selectedMetrics.includes(metric)
      ? selectedMetrics.filter((m) => m !== metric)
      : canonicalOrder.filter(
          (m) => m === metric || selectedMetrics.includes(m),
        );
    setSelectedMetrics(newSelection);
    selectedMetricsPerSplit.current[split] = newSelection;
  };

  const handleSelectAll = () => {
    const newSelection = Object.keys(filteredMetrics);
    setSelectedMetrics(newSelection);
    selectedMetricsPerSplit.current[split] = newSelection;
  };

  const handleClearAll = () => {
    setSelectedMetrics([]);
    selectedMetricsPerSplit.current[split] = [];
  };

  const handleLevelChange = (newLevel) => {
    setLevel(newLevel);
  };

  return (
    <Box p={2}>
      <Box display="flex" justifyContent="flex-end" mb={4}>
        <ToggleButtonGroup
          value={split}
          exclusive
          onChange={(e, newValue) => {
            if (newValue !== null) setSplit(newValue);
          }}
          size="small"
        >
          <ToggleButton value="TRAIN">{t("models:label.train")}</ToggleButton>
          <ToggleButton value="VALIDATION">
            {t("models:label.validation")}
          </ToggleButton>
          <ToggleButton value="TEST">{t("models:label.test")}</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <ResultsGraphsParameters
        currentMetrics={Object.keys(filteredMetrics)}
        selectedMetrics={selectedMetrics}
        handleToggleMetric={handleToggleMetric}
        handleSelectAll={handleSelectAll}
        handleClearAll={handleClearAll}
      />

      <Box sx={{ mb: 4 }} />

      {panels.length === 0 ? (
        <Box
          height={350}
          display="flex"
          alignItems="center"
          justifyContent="center"
          border="1px dashed grey"
        >
          <Typography color="textSecondary">
            {t("models:label.noMetricsAvailableForThisView")}
          </Typography>
        </Box>
      ) : (
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
              sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2 }}
            >
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: 600, mb: 1, px: 1 }}
              >
                {panel.metric}
              </Typography>
              <Plot
                data={[
                  {
                    type: "scatter",
                    mode: panel.x.length > 1 ? "lines" : "markers",
                    x: panel.x,
                    y: panel.y,
                    line: {
                      color: panel.color,
                      width: 2,
                      shape: "spline",
                      smoothing: 0.7,
                    },
                    marker: { color: panel.color },
                    hovertemplate: "%{x}: %{y:.4f}<extra></extra>",
                  },
                ]}
                layout={{
                  autosize: true,
                  height: 240,
                  margin: { l: 50, r: 12, t: 8, b: 40 },
                  showlegend: false,
                  paper_bgcolor: theme.palette.background.paper,
                  plot_bgcolor: theme.palette.background.paper,
                  font: {
                    color: theme.palette.text.primary,
                    family: theme.typography.fontFamily,
                    size: 11,
                  },
                  xaxis: {
                    title: levelLabel,
                    gridcolor: theme.palette.divider,
                    zerolinecolor: theme.palette.divider,
                    tickfont: { color: theme.palette.text.primary, size: 10 },
                  },
                  yaxis: {
                    gridcolor: theme.palette.divider,
                    tickfont: { color: theme.palette.text.primary, size: 10 },
                    automargin: true,
                  },
                }}
                useResizeHandler
                style={{ width: "100%", height: "240px" }}
                config={{ responsive: true, displayModeBar: false }}
              />
            </Box>
          ))}
        </Box>
      )}

      <Box display="flex" justifyContent="flex-end" mt={2}>
        <ButtonGroup size="small" variant="outlined">
          <Button
            variant={level === "TRIAL" ? "contained" : "outlined"}
            onClick={() => handleLevelChange("TRIAL")}
            disabled={!hasTrialData}
          >
            {t("models:label.trial")}
          </Button>
          <Button
            variant={level === "STEP" ? "contained" : "outlined"}
            onClick={() => handleLevelChange("STEP")}
            disabled={!hasStepData}
          >
            {t("models:label.step")}
          </Button>
          <Button
            variant={level === "EPOCH" ? "contained" : "outlined"}
            onClick={() => handleLevelChange("EPOCH")}
            disabled={!hasEpochData}
          >
            {t("models:label.epoch")}
          </Button>
        </ButtonGroup>
      </Box>
    </Box>
  );
}

export default LiveMetricsChart;
