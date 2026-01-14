import React from "react";
import { TextField, FormControlLabel, Switch, Box } from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";
import { useTranslation } from "react-i18next";

export default function LegendForm({ layout, handleChange }) {
  const { t } = useTranslation(["datasets"]);

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
        label={t("datasets:label.showLegend")}
      />

      <TextField
        select
        label={t("datasets:label.legendPosition")}
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
        <option value="v">{t("common:vertical")}</option>
        <option value="h">{t("common:horizontal")}</option>
      </TextField>

      <Box sx={{ display: "flex", gap: 2 }}>
        <TextField
          label={t("datasets:label.legendXPosition")}
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
          label={t("datasets:label.legendYPosition")}
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
        label={t("datasets:label.legendBackgroundColor")}
        value={layout.legend?.bgcolor || "#FFFFFF"}
        onChange={(color) =>
          handleChange("legend", { ...layout.legend, bgcolor: color })
        }
      />

      <DebouncedColorPicker
        label={t("datasets:label.legendBorderColor")}
        value={layout.legend?.bordercolor || "#000000"}
        onChange={(color) =>
          handleChange("legend", { ...layout.legend, bordercolor: color })
        }
      />

      <TextField
        label={t("datasets:label.legendBorderWidth")}
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
