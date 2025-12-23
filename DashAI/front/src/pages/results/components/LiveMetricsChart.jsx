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
import { getExperimentById } from "../../../api/experiment";

export function LiveMetricsChart({ run }) {
  const [level, setLevel] = useState(null);
  const [split, setSplit] = useState("TRAIN");
  const [data, setData] = useState({});
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [availableMetrics, setAvailableMetrics] = useState({
    TRAIN: [], VALIDATION: [], TEST: [],
  });
  const hasUserSelectedMetrics = useRef(false);
  const socketRef = useRef(null);

  /* ---------------- Load test metrics from run data ---------------- */
  useEffect(() => {
    // Check if run is finished (status 3) and has test metrics
    if (run.status === 3 && run.test_metrics) {
      setData((prev) => {
        const next = structuredClone(prev);
        next.TEST = {
          TRIAL: run.test_metrics,
          STEP: run.test_metrics,
          EPOCH: run.test_metrics,
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
            next[splitKey][levelKey] = incoming[splitKey][levelKey];
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
          next.TEST = {
            TRIAL: run.test_metrics,
            STEP: run.test_metrics,
            EPOCH: run.test_metrics,
          };
          return next;
        });
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socketRef.current = ws;

    return () => ws.close();
  }, [run.id, run.test_metrics]);

  useEffect(() => {
    let mounted = true;

    getExperimentById(run.experiment_id).then((exp) => {
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

  const chartData =
    Object.keys(filteredMetrics).length > 0 && Object.values(filteredMetrics)[0]
      ? filteredMetrics[Object.keys(filteredMetrics)[0]].map((_, idx) => {
          const point = { x: idx + 1 };
          for (const key in filteredMetrics) {
            point[key] = filteredMetrics[key][idx];
          }
          return point;
        })
      : [];

  /* ---------------- Sync Level with Split ---------------- */
  const hasTrialData = data[split]?.TRIAL && Object.keys(data[split].TRIAL).length > 0;
  const hasStepData = data[split]?.STEP && Object.keys(data[split].STEP).length > 0;
  const hasEpochData = data[split]?.EPOCH && Object.keys(data[split].EPOCH).length > 0;

  useEffect(() => {
    // Determine the best available level for the new split
    if (hasEpochData) setLevel("EPOCH");
    else if (hasStepData) setLevel("STEP");
    else if (hasTrialData) setLevel("TRIAL");
    else setLevel(null); // Reset if no data exists for this split
  }, [split, hasEpochData, hasStepData, hasTrialData]);

  /* ---------------- Sync Metrics with Split/Level ---------------- */
  useEffect(() => {
    const metricNames = Object.keys(filteredMetrics);
    
    if (metricNames.length === 0) {
      setSelectedMetrics([]);
      return;
    }

    // If user hasn't touched it, auto-select all
    if (!hasUserSelectedMetrics.current) {
      setSelectedMetrics(metricNames);
    } else {
      // If user HAS touched it, filter out metrics that no longer exist in this split
      setSelectedMetrics((prev) => prev.filter(m => metricNames.includes(m)));
    }
  }, [split, level, filteredMetrics]);

  /* ---------------- Reset user selection flag when split changes ---------------- */
  useEffect(() => {
    hasUserSelectedMetrics.current = false;
  }, [split]);

  const handleMetricChange = (e) => {
    hasUserSelectedMetrics.current = true;
    setSelectedMetrics(e.target.value);
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
          <InputLabel>Metrics</InputLabel>
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
        <Tab label="Train" value="TRAIN" />
        <Tab label="Validation" value="VALIDATION" />
        <Tab label="Test" value="TEST" />
      </Tabs>

      {chartData.length === 0 || selectedMetrics.length === 0 ? (
        <Box height={350} display="flex" alignItems="center" justifyContent="center" border="1px dashed grey">
          <Typography color="textSecondary">No metrics available for this view</Typography>
        </Box>
      ) : (
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={chartData}>
            <XAxis
              dataKey="x"
              label={{ value: level, position: "insideBottom", offset: -5 }}
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
            onClick={() => setLevel("TRIAL")}
            disabled={!hasTrialData}
          >
            Trial
          </Button>
          <Button
            variant={level === "STEP" ? "contained" : "outlined"}
            onClick={() => setLevel("STEP")}
            disabled={!hasStepData}
          >
            Step
          </Button>
          <Button
            variant={level === "EPOCH" ? "contained" : "outlined"}
            onClick={() => setLevel("EPOCH")}
            disabled={!hasEpochData}
          >
            Epoch
          </Button>
        </ButtonGroup>
      </Box>
    </Box>
  );
}

export default LiveMetricsChart;
