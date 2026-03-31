import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Tabs,
  Tab,
  Typography,
  Button,
  ButtonGroup,
} from "@mui/material";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { getModelSessionById } from "../../api/modelSession";
import {
  formatScalarMetricsForChart,
  isFiniteMetricValue,
} from "../../utils/metricUtils";

export function LiveMetricsChart({ run }) {
  const { t } = useTranslation("models");
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

        const formattedTestMetrics = formatScalarMetricsForChart(
          run.test_metrics,
        );

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

    const apiUrl = process.env.REACT_APP_API_URL || `${window.location.origin}`;
    let wsUrl;
    try {
      wsUrl = new URL(`/api/v1/metrics/ws/${run.id}`, apiUrl);
    } catch (e) {
      console.error("Invalid WebSocket base URL:", apiUrl, e);
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

          const formattedTestMetrics = formatScalarMetricsForChart(
            run.test_metrics,
          );

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

  const chartData = useMemo(() => {
    if (Object.keys(filteredMetrics).length === 0) return [];

    const allSteps = new Set();
    for (const metricName in filteredMetrics) {
      const metricData = filteredMetrics[metricName];
      if (Array.isArray(metricData)) {
        metricData.forEach((point) => {
          allSteps.add(point.step);
        });
      }
    }

    const sortedSteps = Array.from(allSteps).sort((a, b) => a - b);

    return sortedSteps.map((step) => {
      const point = { x: step };
      for (const metricName in filteredMetrics) {
        const metricData = filteredMetrics[metricName];
        if (Array.isArray(metricData)) {
          const dataPoint = metricData.find((p) => p.step === step);
          point[metricName] = dataPoint?.value ?? null;
        } else {
          point[metricName] = null;
        }
      }
      return point;
    });
  }, [filteredMetrics]);

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

  const handleMetricChange = (e) => {
    const newSelection = e.target.value;
    setSelectedMetrics(newSelection);
    selectedMetricsPerSplit.current[split] = newSelection;
  };

  const handleLevelChange = (newLevel) => {
    setLevel(newLevel);
  };

  return (
    <Box p={2}>
      <Box display="flex" gap={2} mb={2}>
        <FormControl
          size="small"
          sx={{ minWidth: 250 }}
          disabled={Object.keys(filteredMetrics).length === 0}
        >
          <InputLabel>{t("models:label.metrics")}</InputLabel>
          <Select
            multiple
            value={selectedMetrics}
            label="Metrics"
            onChange={handleMetricChange}
            renderValue={(selected) => selected.join(", ")}
          >
            {Object.keys(filteredMetrics).map((metric) => (
              <MenuItem key={metric} value={metric}>
                {metric}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Tabs value={split} onChange={(_, v) => setSplit(v)} sx={{ mb: 2 }}>
        <Tab label={t("models:label.train")} value="TRAIN" />
        <Tab label={t("models:label.validation")} value="VALIDATION" />
        <Tab label={t("models:label.test")} value="TEST" />
      </Tabs>

      {chartData.length === 0 || selectedMetrics.length === 0 ? (
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
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={chartData}>
            <XAxis
              dataKey="x"
              label={{
                value: levelLabel,
                position: "insideBottom",
                offset: -5,
              }}
            />
            <YAxis />
            <Tooltip />
            <Legend />

            {selectedMetrics.map((metric, idx) => (
              <Line
                key={metric}
                type="monotone"
                dataKey={metric}
                dot={false}
                stroke={`hsl(${(idx * 137.5) % 360}, 70%, 50%)`}
                strokeWidth={2}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
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
