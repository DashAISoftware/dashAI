import React from "react";
import { TextField } from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";
import ColorscaleSelector from "../ColorscaleSelector";

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
  return (
    <>
      {/* Common trace settings */}
      <TextField
        label="Name"
        variant="filled"
        value={trace.name || ""}
        onChange={(e) => handleTraceChange(index, "name", e.target.value)}
        fullWidth
      />

      {/* --- Scatter Plot Options --- */}
      {!usesColormap(trace) && (
        <>
          <DebouncedColorPicker
            label="Marker Color"
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
            label="Colorbar Border Color"
            value={trace.colorbar?.bordercolor || "#FFFFFF"}
            onChange={(color) =>
              handleTraceChange(index, "colorbar.bordercolor", color)
            }
          />
          <TextField
            label="Colorbar Border Width"
            variant="filled"
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
    </>
  );
}
