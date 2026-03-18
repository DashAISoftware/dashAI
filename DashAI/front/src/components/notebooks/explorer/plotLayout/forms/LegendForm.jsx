import React from "react";
import { TextField, FormControlLabel, Switch, Box, Divider, Typography } from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";
import { useTranslation } from "react-i18next";

const SectionLabel = ({ children }) => (
  <Typography
    variant="overline"
    color="text.secondary"
    sx={{ lineHeight: 1.5, display: "block" }}
  >
    {children}
  </Typography>
);

export default function LegendForm({ layout, handleChange }) {
  const { t } = useTranslation(["datasets", "common"]);

  return (
    <>
      {/* Visibility & Orientation */}
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

      <Divider />

      {/* Position */}
      <SectionLabel>{t("datasets:label.position", "Position")}</SectionLabel>

      <Box sx={{ display: "flex", gap: 2 }}>
        <TextField
          label={t("datasets:label.legendXPosition")}
          variant="filled"
          type="number"
          value={layout.legend?.x ?? 1}
          onChange={(e) =>
            handleChange("legend", {
              ...layout.legend,
              x: parseFloat(e.target.value),
            })
          }
          fullWidth
          slotProps={{ htmlInput: { step: 0.1, min: -2, max: 3 } }}
          helperText={t(
            "datasets:label.legendPositionHelper",
            "0 = left, 1 = right",
          )}
        />
        <TextField
          label={t("datasets:label.legendYPosition")}
          variant="filled"
          type="number"
          value={layout.legend?.y ?? 1}
          onChange={(e) =>
            handleChange("legend", {
              ...layout.legend,
              y: parseFloat(e.target.value),
            })
          }
          fullWidth
          slotProps={{ htmlInput: { step: 0.1, min: -2, max: 3 } }}
          helperText={t(
            "datasets:label.legendPositionHelper2",
            "0 = bottom, 1 = top",
          )}
        />
      </Box>

      <Divider />

      {/* Appearance */}
      <SectionLabel>{t("datasets:label.appearance", "Appearance")}</SectionLabel>

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
        value={layout.legend?.borderwidth ?? 0}
        onChange={(e) =>
          handleChange("legend", {
            ...layout.legend,
            borderwidth: parseInt(e.target.value, 10) || 0,
          })
        }
        fullWidth
        slotProps={{ htmlInput: { min: 0, max: 10 } }}
      />
    </>
  );
}
