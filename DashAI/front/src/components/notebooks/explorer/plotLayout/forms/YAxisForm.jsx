import React from "react";
import {
  TextField,
  FormControlLabel,
  Switch,
  Box,
  Typography,
  useTheme,
} from "@mui/material";

import DebouncedColorPicker from "../DebouncedColorPicker";
import { useTranslation } from "react-i18next";

export default function YAxisForm({
  data,
  layout,
  handleAxisChange,
  handleTraceChange,
}) {
  const { t } = useTranslation(["datasets"]);
  const theme = useTheme();
  const tickvalsArray = Array.isArray(data[0]?.y) ? data[0].y : [];

  return (
    <>
      <TextField
        label={t("datasets:label.axisTitle", { axis: "Y" })}
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
        label={t("datasets:label.axisFontSize", { axis: "Y" })}
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
        label={t("datasets:label.axisTitleColor", { axis: "Y" })}
        value={layout.yaxis?.title?.font?.color || theme.palette.text.primary}
        onChange={(color) =>
          handleAxisChange("yaxis", "title", {
            ...layout.yaxis?.title,
            font: { ...layout.yaxis?.title?.font, color },
          })
        }
      />

      <TextField
        label={t("datasets:label.axisTitleStandoff", { axis: "Y" })}
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
        label={t("datasets:label.axisTickFontColor", { axis: "Y" })}
        value={layout.yaxis?.tickfont?.color || theme.palette.text.secondary}
        onChange={(color) =>
          handleAxisChange("yaxis", "tickfont", {
            ...layout.yaxis?.tickfont,
            color,
          })
        }
      />

      <TextField
        label={t("datasets:label.axisTickLabel", { axis: "Y" })}
        variant="filled"
        type="number"
        value={layout.yaxis?.tickangle || 0}
        onChange={(e) =>
          handleAxisChange("yaxis", "tickangle", parseInt(e.target.value))
        }
        fullWidth
      />

      <DebouncedColorPicker
        label={t("datasets:label.axisLineColor", { axis: "Y" })}
        value={layout.yaxis?.linecolor || theme.palette.text.primary}
        onChange={(color) => handleAxisChange("yaxis", "linecolor", color)}
      />

      <TextField
        label={t("datasets:label.axisLineWidth", { axis: "Y" })}
        variant="filled"
        type="number"
        value={layout.yaxis?.linewidth || 1}
        onChange={(e) =>
          handleAxisChange("yaxis", "linewidth", parseInt(e.target.value))
        }
        fullWidth
      />

      <DebouncedColorPicker
        label={t("datasets:label.axisGridColor", { axis: "Y" })}
        value={layout.yaxis?.gridcolor || theme.palette.ui.divider}
        onChange={(color) => handleAxisChange("yaxis", "gridcolor", color)}
      />

      <TextField
        label={t("datasets:label.axisGridWidth", { axis: "Y" })}
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
        label={t("datasets:label.showGrid", { axis: "Y" })}
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
        label={t("datasets:label.showZeroLine", { axis: "Y" })}
      />
      {/* Y Axis Tick Labels */}
      {tickvalsArray.length > 0 &&
        tickvalsArray.map((tick, idx) => {
          const rawTicktext = data[0].y[idx];

          return (
            <Box key={`ytick-${tick}`}>
              {/* Label input */}
              <TextField
                label={t("datasets:label.axisTickLabel", { axis: "Y", tick })}
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
