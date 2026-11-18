import { useCallback, useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import { getLoadedModels, unloadModel } from "../../api/loadedModels";
import { formatBytes } from "./formatBytes";

function formatLastUsed(value) {
  // The backend sends UTC datetimes, possibly without a timezone suffix.
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  return new Date(iso).toLocaleTimeString();
}

function formatParams(params) {
  if (!params || Object.keys(params).length === 0) return "";
  return Object.entries(params)
    .map(([key, val]) => `${key}: ${JSON.stringify(val)}`)
    .join(", ");
}

/**
 * Models kept loaded by the job worker. Refreshes whenever `tick` changes, so
 * it follows the hardware panel's own update cadence and never polls on its
 * own; the panel is only mounted while the popover is open.
 */
export default function LoadedModelsSection({ tick }) {
  const { t } = useTranslation(["common"]);
  const [models, setModels] = useState([]);
  const [pendingIds, setPendingIds] = useState([]);
  const [error, setError] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const list = await getLoadedModels();
      if (!mounted.current) return;
      setModels(list);
      // Rows that vanished from the list are no longer pending.
      setPendingIds((prev) =>
        prev.filter((id) => list.some((m) => m.id === id)),
      );
    } catch (e) {
      console.error("Failed to fetch loaded models:", e);
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [tick, refresh]);

  const handleUnload = async (id) => {
    setError(false);
    setPendingIds((prev) => [...prev, id]);
    try {
      await unloadModel(id);
    } catch (e) {
      if (e?.response?.status === 404) {
        // Already gone: just refresh, no error.
        setPendingIds((prev) => prev.filter((p) => p !== id));
      } else {
        console.error("Failed to unload model:", e);
        setPendingIds((prev) => prev.filter((p) => p !== id));
        if (mounted.current) setError(true);
      }
    }
    inFlight.current = false;
    refresh();
  };

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        {t("common:hardwareMonitor.loadedModels.title")}
      </Typography>
      {models.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          {t("common:hardwareMonitor.loadedModels.empty")}
        </Typography>
      )}
      {models.map((model) => {
        const pending = model.unload_requested || pendingIds.includes(model.id);
        const params = formatParams(model.load_params);
        const memory = [
          model.ram_bytes != null && `~${formatBytes(model.ram_bytes)} RAM`,
          model.gpu_bytes != null && `~${formatBytes(model.gpu_bytes)} GPU`,
        ]
          .filter(Boolean)
          .join(" · ");
        return (
          <Box
            key={model.id}
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 4,
              mb: 4,
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Typography variant="body2" fontWeight={500} noWrap>
                  {model.label}
                </Typography>
                <Chip label={model.slot} size="small" variant="outlined" />
                {model.in_use && (
                  <Chip
                    label={t("common:hardwareMonitor.loadedModels.inUse")}
                    size="small"
                    color="info"
                  />
                )}
              </Box>
              {params && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  noWrap
                >
                  {params}
                </Typography>
              )}
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                {[
                  memory,
                  t("common:hardwareMonitor.loadedModels.lastUsed", {
                    time: formatLastUsed(model.last_used_at),
                  }),
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </Typography>
            </Box>
            <Button
              size="small"
              variant="outlined"
              disabled={model.in_use || pending}
              onClick={() => handleUnload(model.id)}
            >
              {pending
                ? t("common:hardwareMonitor.loadedModels.unloading")
                : t("common:hardwareMonitor.loadedModels.unload")}
            </Button>
          </Box>
        );
      })}
      {error && (
        <Typography variant="caption" color="error">
          {t("common:hardwareMonitor.loadedModels.error")}
        </Typography>
      )}
    </Box>
  );
}
