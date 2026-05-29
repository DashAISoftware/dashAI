import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import Chip from "@mui/material/Chip";
import { useTranslation } from "react-i18next";

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "N/A";
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(0)} MB`;
}

function UsageBar({ label, value, detail, color = "primary" }) {
  const percent = value ?? 0;

  return (
    <Box sx={{ mb: 6 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="body2" fontWeight={500}>
          {label}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {value !== null ? `${percent.toFixed(1)}%` : "N/A"}
          {detail ? ` · ${detail}` : ""}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={Math.min(percent, 100)}
        color={color}
        sx={{ height: 6, borderRadius: 1 }}
      />
    </Box>
  );
}

export default function HardwareMonitorPanel({ stats, connected }) {
  const { t } = useTranslation(["common"]);

  if (!connected || !stats) {
    return (
      <Box sx={{ p: 8, minWidth: 320 }}>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          {t("common:hardwareMonitor.connecting")}
        </Typography>
      </Box>
    );
  }

  const { cpu, ram, gpus } = stats;

  return (
    <Box sx={{ p: 4, minWidth: 320, maxWidth: 400 }}>
      <Typography variant="subtitle2" gutterBottom>
        {t("common:hardwareMonitor.cpu")}
        {cpu.frequency_mhz != null && (
          <Typography
            component="span"
            variant="caption"
            color="text.secondary"
            sx={{ ml: 4 }}
          >
            {cpu.frequency_mhz.toFixed(0)} MHz · {cpu.cores_physical}C/
            {cpu.cores_logical}T
          </Typography>
        )}
      </Typography>
      <UsageBar
        label={t("common:hardwareMonitor.overall")}
        value={cpu.percent}
        color="primary"
      />

      <Divider sx={{ my: 6 }} />

      <Typography variant="subtitle2" gutterBottom>
        {t("common:hardwareMonitor.ram")}
      </Typography>
      <UsageBar
        label={`${formatBytes(ram.used)} / ${formatBytes(ram.total)}`}
        value={ram.percent}
        color="info"
      />

      {gpus.length > 0 && (
        <>
          <Divider sx={{ my: 6 }} />
          <Typography variant="subtitle2" gutterBottom>
            {t("common:hardwareMonitor.gpu")}
          </Typography>
          {gpus.map((gpu, idx) => (
            <Box key={gpu.name} sx={{ mb: idx < gpus.length - 1 ? 8 : 0 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  mb: 2,
                }}
              >
                <Typography variant="body2" fontWeight={500} noWrap>
                  {gpu.name}
                </Typography>
                <Chip label={gpu.vendor} size="small" variant="outlined" />
                {gpu.temperature != null && (
                  <Typography variant="caption" color="text.secondary">
                    {gpu.temperature}°C
                  </Typography>
                )}
              </Box>
              <UsageBar
                label={t("common:hardwareMonitor.utilization")}
                value={gpu.utilization}
                color="secondary"
              />
              {gpu.memory_percent != null && (
                <UsageBar
                  label={`VRAM · ${formatBytes(gpu.memory_used)} / ${formatBytes(gpu.memory_total)}`}
                  value={gpu.memory_percent}
                  color="warning"
                />
              )}
            </Box>
          ))}
        </>
      )}
    </Box>
  );
}
