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
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { getModelSessionById } from "../../../api/modelSession";

export function LiveMetricsChart({ run }) {
  const { t } = useTranslation(["models", "common"]);
  const [level, setLevel] = useState(null);
  const [split, setSplit] = useState("TRAIN");
  const [data, setData] = useState({});
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [availableMetrics, setAvailableMetrics] = useState({
    TRAIN: [],
    VALIDATION: [],
    TEST: [],
  });

  // Track user selections per split
  const selectedMetricsPerSplit = useRef({
    TRAIN: null,
    VALIDATION: null,
    TEST: null,
  });
  const socketRef = useRef(null);

  /* ---------------- Load test metrics from run data ---------------- */
  useEffect(() => {
    // Check if run is finished (status 3) and has test metrics
    if (run.status === 3 && run.test_metrics) {
      setData((prev) => {
        const next = structuredClone(prev);

        // Convert old format to new format if needed
        const formattedTestMetrics = {};
        for (const metricName in run.test_metrics) {
          const metricData = run.test_metrics[metricName];
          // Check if it's already in new format (array of objects)
          if (Array.isArray(metricData)) {
            formattedTestMetrics[metricName] = metricData;
          } else {
            // Handle new format (object with value and std_value) or old format (single value)
            const value = metricData?.value ?? metricData;
            // Convert to new format
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

  /* ---------------- WebSocket ---------------- */
  useEffect(() => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    const ws = new WebSocket(`ws://localhost:8000/api/v1/metrics/ws/${run.id}`);

    ws.onmessage = (event) => {
      const incoming = JSON.parse(event.data);

      setData((prev) => {
        const next = structuredClone(prev);

        for (const splitKey in incoming) {
          if (splitKey === "run_status") continue;
          next[splitKey] ??= {};

          for (const levelKey in incoming[splitKey]) {
            next[splitKey][levelKey] ??= {};

            // incoming[splitKey][levelKey] is now { metric_name: [data_points] }
            for (const metricName in incoming[splitKey][levelKey]) {
              const incomingPoints = incoming[splitKey][levelKey][metricName];

              if (!Array.isArray(next[splitKey][levelKey][metricName])) {
                // First time seeing this metric -> create array
                next[splitKey][levelKey][metricName] = [...incomingPoints];
              } else {
                // Metric already exists -> append only new points
                next[splitKey][levelKey][metricName].push(...incomingPoints);
              }
            }
          }
        }

        return next;
      });
    };

    ws.onclose = () => {
      // When WebSocket closes, load test metrics if available
      if (run.test_metrics) {
        setData((prev) => {
          const next = structuredClone(prev);

          // Convert old format to new format if needed
          const formattedTestMetrics = {};
          for (const metricName in run.test_metrics) {
            const metricData = run.test_metrics[metricName];
            // Check if it's already in new format (array of objects)
            if (Array.isArray(metricData)) {
              formattedTestMetrics[metricName] = metricData;
            } else {
              // Handle new format (object with value and std_value) or old format (single value)
              const value = metricData?.value ?? metricData;
              // Convert to new format
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
  }, [run.id, run.test_metrics]);

  useEffect(() => {
    let mounted = true;

    getModelSessionById(run.model_session_id).then((exp) => {
      if (!mounted) return;

      setAvailableMetrics({
        TRAIN: exp.train_metrics ?? [],
        VALIDATION: exp.validation_metrics ?? [],
        TEST: exp.test_metrics ?? [],
      });
    });

    return () => {
      mounted = false;
    };
  }, [run.experiment_id]);

  /* ---------------- Chart data ---------------- */
  const metrics = data[split]?.[level] ?? {};
  const allowed = availableMetrics[split] ?? [];

  const filteredMetrics = Object.fromEntries(
    Object.entries(metrics).filter(([name]) => allowed.includes(name)),
  );

  // Transform new data structure to chart format
  const chartData = (() => {
    if (Object.keys(filteredMetrics).length === 0) return [];

    // Get all unique steps across all metrics
    const allSteps = new Set();
    for (const metricName in filteredMetrics) {
      const metricData = filteredMetrics[metricName];

      // Safety check: ensure it's an array
      if (Array.isArray(metricData)) {
        metricData.forEach((point) => {
          allSteps.add(point.step);
        });
      }
    }

    // Sort steps
    const sortedSteps = Array.from(allSteps).sort((a, b) => a - b);

    // Build chart data points
    return sortedSteps.map((step) => {
      const point = { x: step };

      for (const metricName in filteredMetrics) {
        const metricData = filteredMetrics[metricName];

        // Safety check: ensure it's an array
        if (Array.isArray(metricData)) {
          // Find the data point for this step
          const dataPoint = metricData.find((p) => p.step === step);
          point[metricName] = dataPoint?.value ?? null;
        } else {
          point[metricName] = null;
        }
      }

      return point;
    });
  })();

  /* ---------------- Sync Level with Split ---------------- */
  const hasTrialData =
    data[split]?.TRIAL && Object.keys(data[split].TRIAL).length > 0;
  const hasStepData =
    data[split]?.STEP && Object.keys(data[split].STEP).length > 0;
  const hasEpochData =
    data[split]?.EPOCH && Object.keys(data[split].EPOCH).length > 0;

  useEffect(() => {
    // Check if current level has data in the new split
    const currentLevelHasData =
      (level === "TRIAL" && hasTrialData) ||
      (level === "STEP" && hasStepData) ||
      (level === "EPOCH" && hasEpochData);

    // If selected a level and it has data in the new split, keep it
    if (currentLevelHasData) {
      return;
    }

    // Otherwise, auto-select the best available level
    if (hasEpochData) setLevel("EPOCH");
    else if (hasStepData) setLevel("STEP");
    else if (hasTrialData) setLevel("TRIAL");
    else setLevel(null);
  }, [split, hasEpochData, hasStepData, hasTrialData, level]);

  /* ---------------- Sync Metrics with Split/Level ---------------- */
  useEffect(() => {
    const metricNames = Object.keys(filteredMetrics);

    if (metricNames.length === 0) {
      setSelectedMetrics([]);
      return;
    }

    // Check if this split has saved selections
    const savedSelection = selectedMetricsPerSplit.current[split];

    if (savedSelection !== null) {
      // Use saved selection, but filter out metrics that no longer exist
      const validSavedMetrics = savedSelection.filter((m) =>
        metricNames.includes(m),
      );
      setSelectedMetrics(validSavedMetrics);
    } else {
      // No saved selection, auto-select all
      setSelectedMetrics(metricNames);
    }
  }, [split, level, filteredMetrics]);

  const handleMetricChange = (e) => {
    const newSelection = e.target.value;
    setSelectedMetrics(newSelection);
    // Save selection for current split
    selectedMetricsPerSplit.current[split] = newSelection;
  };

  const handleLevelChange = (newLevel) => {
    setLevel(newLevel);
  };

  /* ---------------- Render ---------------- */
  return (
    <Box p={2}>
      <Box display="flex" gap={2} mb={2}>
        <FormControl
          size="small"
          sx={{ minWidth: 250 }}
          disabled={Object.keys(filteredMetrics).length === 0}
        >
          <InputLabel>{t("common:metrics")}</InputLabel>
          <Select
            multiple
            value={selectedMetrics}
            label={t("common:metrics")}
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
        <Tab label={t("common:train")} value="TRAIN" />
        <Tab label={t("common:validation")} value="VALIDATION" />
        <Tab label={t("common:test")} value="TEST" />
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
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={chartData}>
            <XAxis
              dataKey="x"
              label={{
                value: t(`models:label.${level.toLowerCase()}`),
                position: "insideBottom",
                offset: -3,
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
