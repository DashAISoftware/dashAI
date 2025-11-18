import React from "react";

export default function LegendForm({ layout, handleLegendChange }) {
  return (
    <>
      <FormControlLabel
        control={
          <Switch
            checked={layout.showlegend ?? true}
            onChange={(e) => handleChange("showlegend", e.target.checked)}
            color="primary"
          />
        }
        label="Show Legend"
      />

      <TextField
        select
        label="Legend Position"
        variant="filled"
        value={layout.legend?.orientation || "v"}
        onChange={(e) =>
          handleChange("legend", {
            ...layout.legend,
            orientation: e.target.value,
          })
        }
        slotProps={{ select: { native: true } }}
        fullWidth
      >
        <option value="v">Vertical</option>
        <option value="h">Horizontal</option>
      </TextField>

      <Box sx={{ display: "flex", gap: 2 }}>
        <TextField
          label="Legend X Position"
          variant="filled"
          type="number"
          step="0.1"
          value={layout.legend?.x ?? 1}
          onChange={(e) =>
            handleChange("legend", {
              ...layout.legend,
              x: parseFloat(e.target.value),
            })
          }
          fullWidth
        />
        <TextField
          label="Legend Y Position"
          variant="filled"
          type="number"
          step="0.1"
          value={layout.legend?.y ?? 1}
          onChange={(e) =>
            handleChange("legend", {
              ...layout.legend,
              y: parseFloat(e.target.value),
            })
          }
          fullWidth
        />
      </Box>

      <DebouncedColorPicker
        label="Legend Background Color"
        value={layout.legend?.bgcolor || "#FFFFFF"}
        onChange={(color) =>
          handleChange("legend", { ...layout.legend, bgcolor: color })
        }
      />

      <DebouncedColorPicker
        label="Legend Border Color"
        value={layout.legend?.bordercolor || "#000000"}
        onChange={(color) =>
          handleChange("legend", { ...layout.legend, bordercolor: color })
        }
      />

      <TextField
        label="Legend Border Width"
        variant="filled"
        type="number"
        value={layout.legend?.borderwidth || 0}
        onChange={(e) =>
          handleChange("legend", {
            ...layout.legend,
            borderwidth: parseInt(e.target.value),
          })
        }
        fullWidth
      />
    </>
  );
}
