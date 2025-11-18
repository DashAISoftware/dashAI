import React from "react";
import { TextField, FormControlLabel, Switch } from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";

export default function XAxisForm({ layout, handleAxisChange }) {
  return (
    <>
      <TextField
        label="X Axis Title"
        variant="filled"
        value={layout.xaxis?.title?.text || ""}
        onChange={(e) =>
          handleAxisChange("xaxis", "title", {
            ...layout.xaxis?.title,
            text: e.target.value,
          })
        }
        fullWidth
      />

      <TextField
        label="X Axis Font Size"
        variant="filled"
        type="number"
        value={layout.xaxis?.title?.font?.size || 14}
        onChange={(e) =>
          handleAxisChange("xaxis", "title", {
            ...layout.xaxis?.title,
            font: {
              ...layout.xaxis?.title?.font,
              size: parseInt(e.target.value),
            },
          })
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="X Axis Title Color"
        value={layout.xaxis?.title?.font?.color || "#2A3F5F"}
        onChange={(color) =>
          handleAxisChange("xaxis", "title", {
            ...layout.xaxis?.title,
            font: { ...layout.xaxis?.title?.font, color },
          })
        }
      />

      <TextField
        label="X Axis Title Standoff"
        variant="filled"
        type="number"
        value={layout.xaxis?.title?.standoff || 15}
        onChange={(e) =>
          handleAxisChange("xaxis", "title", {
            ...layout.xaxis?.title,
            standoff: parseInt(e.target.value),
          })
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="X Axis Tick Color"
        value={layout.xaxis?.tickfont?.color || "#2A3F5F"}
        onChange={(color) =>
          handleAxisChange("xaxis", "tickfont", {
            ...layout.xaxis?.tickfont,
            color,
          })
        }
      />
      <TextField
        label="X Axis Tick Angle"
        variant="filled"
        type="number"
        value={layout.xaxis?.tickangle || 0}
        onChange={(e) =>
          handleAxisChange("xaxis", "tickangle", parseInt(e.target.value))
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="X Axis Line Color"
        value={layout.xaxis?.linecolor || "#FFFFFF"}
        onChange={(color) => handleAxisChange("xaxis", "linecolor", color)}
      />

      <TextField
        label="X Axis Line Width"
        variant="filled"
        type="number"
        value={layout.xaxis?.linewidth || 1}
        onChange={(e) =>
          handleAxisChange("xaxis", "linewidth", parseInt(e.target.value))
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="X Axis Grid Color"
        value={layout.xaxis?.gridcolor || "#FFFFFF"}
        onChange={(color) => handleAxisChange("xaxis", "gridcolor", color)}
      />

      <TextField
        label="X Axis Grid Width"
        variant="filled"
        type="number"
        value={layout.xaxis?.gridwidth || 1}
        onChange={(e) =>
          handleAxisChange("xaxis", "gridwidth", parseInt(e.target.value))
        }
        fullWidth
      />

      <FormControlLabel
        control={
          <Switch
            checked={layout.xaxis?.showgrid ?? true}
            onChange={(e) =>
              handleAxisChange("xaxis", "showgrid", e.target.checked)
            }
            color="primary"
          />
        }
        label="Show Grid"
      />

      <FormControlLabel
        control={
          <Switch
            checked={layout.xaxis?.zeroline ?? true}
            onChange={(e) =>
              handleAxisChange("xaxis", "zeroline", e.target.checked)
            }
            color="primary"
          />
        }
        label="Show Zero Line"
      />
    </>
  );
}
