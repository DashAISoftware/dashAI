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

  // px.imshow() (correlation matrix, density heatmap) sets coloraxis: "coloraxis"
  // on the trace, so the colorbar lives in layout.coloraxis.colorbar — not trace.colorbar.
  // Other heatmap types that don't reference a shared coloraxis keep their colorbar
  // directly on the trace.
  const colorbarInLayout = Boolean(trace.coloraxis);
  const colorbarSrc = colorbarInLayout
    ? layout.coloraxis?.colorbar
    : trace.colorbar;

  const setColorbarField = (field, value) => {
    if (colorbarInLayout) {
      handleChange("coloraxis", {
        ...layout.coloraxis,
        colorbar: { ...layout.coloraxis?.colorbar, [field]: value },
      });
    } else {
      handleTraceChange(index, `colorbar.${field}`, value);
    }
  };

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
            value={colorbarSrc?.bordercolor || "#FFFFFF"}
            onChange={(color) => setColorbarField("bordercolor", color)}
          />
          <TextField
            label={t("datasets:label.colorbarBorderWidth")}
            variant="outlined"
            size="small"
            type="number"
            value={colorbarSrc?.borderwidth || 0}
            onChange={(e) =>
              setColorbarField("borderwidth", parseInt(e.target.value))
            }
            fullWidth
          />

          <DebouncedColorPicker
            label={t("datasets:label.colorbarTickFontColor")}
            value={colorbarSrc?.tickfont?.color || "#444444"}
            onChange={(color) =>
              setColorbarField("tickfont", {
                ...colorbarSrc?.tickfont,
                color,
              })
            }
          />
          <TextField
            label={t("datasets:label.colorbarTickFontSize")}
            variant="outlined"
            size="small"
            type="number"
            value={colorbarSrc?.tickfont?.size ?? 12}
            onChange={(e) =>
              setColorbarField("tickfont", {
                ...colorbarSrc?.tickfont,
                size: parseInt(e.target.value, 10) || 12,
              })
            }
            fullWidth
            slotProps={{ htmlInput: { min: 8, max: 72 } }}
          />
        </>
      )}
    </Box>
  );
}
