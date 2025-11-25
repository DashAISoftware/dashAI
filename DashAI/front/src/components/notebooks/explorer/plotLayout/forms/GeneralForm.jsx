import React from "react";
import { Box, TextField } from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";

const FONT_LIST = [
  "Arial",
  "Balto",
  "Courier New",
  "Droid Sans",
  "Droid Serif",
  "Droid Sans Mono",
  "Gravitas One",
  "Old Standard TT",
  "Open Sans",
  "PT Sans Narrow",
  "Raleway",
  "Times New Roman",
];

export default function GeneralForm({ layout, handleChange }) {
  return (
    <>
      <TextField
        label="Title"
        variant="filled"
        value={layout.title?.text || ""}
        onChange={(e) =>
          handleChange("title", { ...layout.title, text: e.target.value })
        }
        fullWidth
      />

      <TextField
        label="Title Font Size"
        variant="filled"
        type="number"
        value={layout.title?.font?.size || 16}
        onChange={(e) =>
          handleChange("title", {
            ...layout.title,
            font: { ...layout.title?.font, size: parseInt(e.target.value) },
          })
        }
        fullWidth
      />

      <DebouncedColorPicker
        label="Title Color"
        value={layout.title?.font?.color || "#2A3F5F"}
        onChange={(color) =>
          handleChange("title", {
            ...layout.title,
            font: { ...layout.title?.font, color },
          })
        }
      />

      <TextField
        select
        label="Font Family"
        variant="filled"
        value={layout.font?.family || "Arial"}
        onChange={(e) =>
          handleChange("font", { ...layout.font, family: e.target.value })
        }
        slotProps={{ select: { native: true } }}
        fullWidth
      >
        {FONT_LIST.map((font) => (
          <option key={font} value={font}>
            {font}
          </option>
        ))}
      </TextField>

      <DebouncedColorPicker
        label="Background Color"
        value={layout.paper_bgcolor || "#ffffff"}
        onChange={(color) => handleChange("paper_bgcolor", color)}
      />

      <DebouncedColorPicker
        label="Plot Background Color"
        value={layout.plot_bgcolor || "#E5ECF6"}
        onChange={(color) => handleChange("plot_bgcolor", color)}
      />

      <Box sx={{ display: "flex", gap: 2 }}>
        <TextField
          label="Margin Left"
          variant="filled"
          type="number"
          value={layout.margin?.l || 80}
          onChange={(e) =>
            handleChange("margin", {
              ...layout.margin,
              l: parseInt(e.target.value),
            })
          }
          fullWidth
        />
        <TextField
          label="Margin Right"
          variant="filled"
          type="number"
          value={layout.margin?.r || 80}
          onChange={(e) =>
            handleChange("margin", {
              ...layout.margin,
              r: parseInt(e.target.value),
            })
          }
          fullWidth
        />
      </Box>

      <Box sx={{ display: "flex", gap: 2 }}>
        <TextField
          label="Margin Top"
          variant="filled"
          type="number"
          value={layout.margin?.t || 100}
          onChange={(e) =>
            handleChange("margin", {
              ...layout.margin,
              t: parseInt(e.target.value),
            })
          }
          fullWidth
        />
        <TextField
          label="Margin Bottom"
          variant="filled"
          type="number"
          value={layout.margin?.b || 80}
          onChange={(e) =>
            handleChange("margin", {
              ...layout.margin,
              b: parseInt(e.target.value),
            })
          }
          fullWidth
        />
      </Box>
    </>
  );
}
