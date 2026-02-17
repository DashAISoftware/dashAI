import React from "react";
import { Box, TextField } from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation(["datasets"]);

  return (
    <>
      <TextField
        label={t("datasets:label.title")}
        variant="filled"
        value={layout.title?.text || ""}
        onChange={(e) =>
          handleChange("title", { ...layout.title, text: e.target.value })
        }
        fullWidth
      />

      <TextField
        label={t("datasets:label.titleFontSize")}
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
        label={t("datasets:label.titleColor")}
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
        label={t("datasets:label.fontFamily")}
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
        label={t("datasets:label.backgroundColor")}
        value={layout.paper_bgcolor || "#ffffff"}
        onChange={(color) => handleChange("paper_bgcolor", color)}
      />

      <DebouncedColorPicker
        label={t("datasets:label.plotBackgroundColor")}
        value={layout.plot_bgcolor || "#E5ECF6"}
        onChange={(color) => handleChange("plot_bgcolor", color)}
      />

      <Box sx={{ display: "flex", gap: 2 }}>
        <TextField
          label={t("datasets:label.marginLeft")}
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
          label={t("datasets:label.marginRight")}
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
          label={t("datasets:label.marginTop")}
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
          label={t("datasets:label.marginBottom")}
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
