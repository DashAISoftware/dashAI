import React from "react";
import { Box, TextField } from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";
import ColorscaleSelector from "../ColorscaleSelector";
import { useTranslation } from "react-i18next";

const usesColormap = (trace) =>
  ["heatmap", "surface", "scatter3d", "choropleth", "histogram2d"].includes(
    trace.type,
  );

export default function TraceForm({
  layout,
  trace,
  index,
  handleTraceChange,
  handleChange,
}) {
  const { t } = useTranslation(["datasets", "common"]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {/* Common trace settings */}
      <TextField
        label={t("common:name")}
        variant="outlined"
        size="small"
        value={trace.name || ""}
        onChange={(e) => handleTraceChange(index, "name", e.target.value)}
        fullWidth
      />

      {/* --- Scatter Plot Options --- */}
      {!usesColormap(trace) && (
        <>
          <DebouncedColorPicker
            label={t("datasets:label.markerColor")}
            value={
              trace.marker?.color ||
              layout.template.layout.colorway[
                index % layout.template.layout.colorway.length
              ] ||
              "#000000"
            }
            onChange={(color) =>
              handleTraceChange(index, "marker.color", color)
            }
          />
        </>
      )}

      {/* --- Heatmap Options --- */}
      {usesColormap(trace) && (
        <>
          <ColorscaleSelector
            value={layout.coloraxis?.colorscale}
            onChange={(newScale) =>
              handleChange("coloraxis", {
                ...layout.coloraxis,
                colorscale: newScale,
              })
            }
          />

          <DebouncedColorPicker
            label={t("datasets:label.colorbarBorderColor")}
            value={trace.colorbar?.bordercolor || "#FFFFFF"}
            onChange={(color) =>
              handleTraceChange(index, "colorbar.bordercolor", color)
            }
          />
          <TextField
            label={t("datasets:label.colorbarBorderWidth")}
            variant="outlined"
            size="small"
            type="number"
            value={trace.colorbar?.borderwidth || 0}
            onChange={(e) =>
              handleTraceChange(
                index,
                "colorbar.borderwidth",
                parseInt(e.target.value),
              )
            }
            fullWidth
          />
        </>
      )}
    </Box>
  );
}
