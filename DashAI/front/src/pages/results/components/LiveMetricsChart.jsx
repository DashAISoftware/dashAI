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
} from "@mui/material"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { useEffect, useRef, useState } from "react"

export function LiveMetricsChart({ runId }) {
  const [level, setLevel] = useState("EPOCH")
  const [split, setSplit] = useState("TRAIN")
  const [data, setData] = useState({})
  const [selectedMetrics, setSelectedMetrics] = useState([])
  const socketRef = useRef(null)
  
  /* ---------------- WebSocket ---------------- */
  useEffect(() => {
    if (socketRef.current) {
      socketRef.current.close()
    }

    const ws = new WebSocket(
      `ws://localhost:8000/api/v1/metrics/ws/${runId}`
    )

    ws.onmessage = (event) => {
      const incoming = JSON.parse(event.data)

      setData((prev) => {
        const next = structuredClone(prev)

        for (const splitKey in incoming) {
          if (splitKey === "run_status") continue
          next[splitKey] ??= {}
          for (const levelKey in incoming[splitKey]) {
            next[splitKey][levelKey] =
              incoming[splitKey][levelKey]
          }
        }

        return next
      })
    }

    ws.onerror = (error) => {
      console.error("WebSocket error:", error)
    }

    socketRef.current = ws

    return () => ws.close()
  }, [runId])


  /* ---------------- Chart data ---------------- */
  const metrics = data[split]?.[level] ?? {}

  const chartData = Object.keys(metrics).length > 0 && Object.values(metrics)[0]
    ? metrics[Object.keys(metrics)[0]].map((_, idx) => {
        const point = { x: idx + 1 }
        for (const key in metrics) {
          point[key] = metrics[key][idx]
        }
        return point
      })
    : []

  /* ---------------- Auto-select metrics ---------------- */
  useEffect(() => {
    const metricNames = Object.keys(metrics)
    if (metricNames.length > 0) {
      setSelectedMetrics(metricNames)
    }
  }, [split, level])

  /* ---------------- Check available levels ---------------- */
  const hasTrialData = data[split]?.TRIAL && Object.keys(data[split].TRIAL).length > 0
  const hasStepData = data[split]?.STEP && Object.keys(data[split].STEP).length > 0
  const hasEpochData = data[split]?.EPOCH && Object.keys(data[split].EPOCH).length > 0

  /* ---------------- Render ---------------- */
  return (
    <Box p={2}>
      <Box display="flex" gap={2} mb={2}>
        <FormControl size="small" sx={{ minWidth: 250 }}>
          <InputLabel>Metrics</InputLabel>
          <Select
            multiple
            value={selectedMetrics}
            label="Metrics"
            onChange={(e) =>
              setSelectedMetrics(e.target.value)
            }
            renderValue={(selected) => selected.join(", ")}
          >
            {Object.keys(metrics).map((metric) => (
              <MenuItem key={metric} value={metric}>
                {metric}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Tabs
        value={split}
        onChange={(_, v) => setSplit(v)}
        sx={{ mb: 2 }}
      >
        <Tab label="Train" value="TRAIN" />
        <Tab label="Validation" value="VALIDATION" />
        <Tab label="Test" value="TEST" />
      </Tabs>

      {Object.keys(metrics).length === 0 ? (
        <Typography>No metrics yet</Typography>
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
                stroke={`hsl(${(idx * 360) / selectedMetrics.length}, 70%, 50%)`}
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
  )
}

export default LiveMetricsChart