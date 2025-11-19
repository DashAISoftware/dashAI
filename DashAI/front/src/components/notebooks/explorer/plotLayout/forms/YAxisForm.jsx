import React from "react";
import {
  TextField,
  FormControlLabel,
  Switch,
  Box,
  Typography,
} from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";

export default function YAxisForm({
  data,
  layout,
  handleAxisChange,
  handleTraceChange,
}) {
  const tickvalsArray = Array.isArray(data[0]?.y) ? data[0].y : [];

  return (
    <>
      <TextField
        label="Y Axis Title"
        variant="filled"
        value={layout.yaxis?.title?.text || ""}
        onChange={(e) =>
          handleAxisChange("yaxis", "title", {
            ...layout.yaxis?.title,
            text: e.target.value,
          })
        }
        fullWidth
      />

      <TextField
        label="Y Axis Font Size"
        variant="filled"
        type="number"
        value={layout.yaxis?.title?.font?.size || 14}
        onChange={(e) =>
          handleAxisChange("yaxis", "title", {
            ...layout.yaxis?.title,
            font: {
              ...layout.yaxis?.title?.font,
              size: parseInt(e.target.value),
            },
          })
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="Y Axis Title Color"
        value={layout.yaxis?.title?.font?.color || "#2A3F5F"}
        onChange={(color) =>
          handleAxisChange("yaxis", "title", {
            ...layout.yaxis?.title,
            font: { ...layout.yaxis?.title?.font, color },
          })
        }
      />

      <TextField
        label="Y Axis Title Standoff"
        variant="filled"
        type="number"
        value={layout.yaxis?.title?.standoff || 15}
        onChange={(e) =>
          handleAxisChange("yaxis", "title", {
            ...layout.yaxis?.title,
            standoff: parseInt(e.target.value),
          })
        }
        fullWidth
      />
      <DebouncedColorPicker
        label="Y Axis Tick Color"
        value={layout.yaxis?.tickfont?.color || "#2A3F5F"}
        onChange={(color) =>
          handleAxisChange("yaxis", "tickfont", {
            ...layout.yaxis?.tickfont,
            color,
          })
        }
      />

      <TextField
        label="Y Axis Tick Angle"
        variant="filled"
        type="number"
        value={layout.yaxis?.tickangle || 0}
        onChange={(e) =>
          handleAxisChange("yaxis", "tickangle", parseInt(e.target.value))
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="Y Axis Line Color"
        value={layout.yaxis?.linecolor || "#FFFFFF"}
        onChange={(color) => handleAxisChange("yaxis", "linecolor", color)}
      />

      <TextField
        label="Y Axis Line Width"
        variant="filled"
        type="number"
        value={layout.yaxis?.linewidth || 1}
        onChange={(e) =>
          handleAxisChange("yaxis", "linewidth", parseInt(e.target.value))
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="Y Axis Grid Color"
        value={layout.yaxis?.gridcolor || "#FFFFFF"}
        onChange={(color) => handleAxisChange("yaxis", "gridcolor", color)}
      />

      <TextField
        label="Y Axis Grid Width"
        variant="filled"
        type="number"
        value={layout.yaxis?.gridwidth || 1}
        onChange={(e) =>
          handleAxisChange("yaxis", "gridwidth", parseInt(e.target.value))
        }
        fullWidth
      />

      <FormControlLabel
        control={
          <Switch
            checked={layout.yaxis?.showgrid ?? true}
            onChange={(e) =>
              handleAxisChange("yaxis", "showgrid", e.target.checked)
            }
            color="primary"
          />
        }
        label="Show Grid"
      />

      <FormControlLabel
        control={
          <Switch
            checked={layout.yaxis?.zeroline ?? true}
            onChange={(e) =>
              handleAxisChange("yaxis", "zeroline", e.target.checked)
            }
            color="primary"
          />
        }
        label="Show Zero Line"
      />
      {/* Y Axis Tick Labels */}
      {tickvalsArray.length > 0 &&
        tickvalsArray.map((tick, idx) => {
          const rawTicktext = data[0].y[idx];

          return (
            <Box
              key={idx}
              sx={{
                mt: 2,
                p: 2,
                border: "1px solid #444",
                borderRadius: 1,
                bgcolor: "#333",
              }}
            >
              {/* Label input */}
              <TextField
                label={`Y Tick Label for ${tick}`}
                variant="filled"
                value={rawTicktext}
                onChange={(e) => {
                  const newTicktext = e.target.value;
                  const newY = [...data[0].y];
                  newY[idx] = newTicktext;

                  handleTraceChange(0, `y`, newY);
                }}
                fullWidth
                sx={{ mb: 2 }}
              />
            </Box>
          );
        })}
    </>
  );
}
