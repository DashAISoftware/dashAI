import { Box, Typography, Paper, Chip } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import ScienceIcon from "@mui/icons-material/Science";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import MetricCard from "./MetricCard";

const splitConfig = {
  train: {
    icon: StorageIcon,
    color: "#4caf50",
    bg: "rgba(76,175,80,0.08)",
  },
  test: {
    icon: ScienceIcon,
    color: "#2196f3",
    bg: "rgba(33,150,243,0.08)",
  },
  validation: {
    icon: CheckCircleIcon,
    color: "#ff9800",
    bg: "rgba(255,152,0,0.08)",
  },
};

export default function SplitColumn({
  title,
  splitType,
  metrics,
  selectedMetrics,
  onToggleMetric,
  disabled = false,
}) {
  const config = splitConfig[splitType];
  const Icon = config.icon;

  return (
    <Paper
      variant="outlined"
      sx={{
        height: "100%",
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? "none" : "auto",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: config.bg,
        }}
      >
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <Icon sx={{ color: config.color }} />
          <Box>
            <Typography variant="subtitle1">{title}</Typography>
            <Typography variant="caption" color="text.secondary">
              {selectedMetrics.length} of {metrics.length} selected
            </Typography>
          </Box>
        </Box>

        <Chip
          label={selectedMetrics.length}
          sx={{
            backgroundColor: config.bg,
            color: config.color,
            fontFamily: "monospace",
          }}
        />
      </Box>

      {/* Metrics */}
      <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
        {metrics.map((metric) => (
          <MetricCard
            key={metric.name}
            metric={metric}
            isSelected={selectedMetrics.includes(metric.name)}
            onToggle={() => onToggleMetric(metric.name)}
            splitType={splitType}
            disabled={disabled}
          />
        ))}
      </Box>
    </Paper>
  );
}
