import React, { useRef, useState } from "react";
import {
  Box,
  TextField,
  Typography,
  FormControlLabel,
  Switch,
  Divider,
  Stack,
  Button,
} from "@mui/material";

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

export default function PlotLayoutForm({ layout, setLayout, onSave }) {
  if (!layout) return null;

  const [modified, setModified] = useState(false);

  const localLayout = useRef(layout);
  const handleChange = (field, value) => {
    setLayout({ ...layout, [field]: value });
    setModified(true);
  };

  const handleCancel = () => {
    setLayout(localLayout.current);
    setModified(false);
  };
  const handleSave = () => {
    localLayout.current = layout;
    setModified(false);
    onSave();
  };

  const handleAxisChange = (axis, field, value) => {
    setLayout({
      ...layout,
      [axis]: { ...layout[axis], [field]: value },
    });
    setModified(true);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        width: "100%",
        bgcolor: "#1e1e1e",
        color: "white",
        p: 3,
        borderRadius: 2,
        boxShadow: 2,
      }}
    >
      <Typography variant="h6" sx={{ mb: 1 }}>
        Edit Plot Layout
      </Typography>

      <TextField
        label="Title"
        variant="filled"
        value={layout.title?.text || ""}
        onChange={(e) =>
          handleChange("title", { ...layout.title, text: e.target.value })
        }
        fullWidth
      />
      {/* Font Size */}
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

      <Divider sx={{ my: 1, borderColor: "#444" }} />

      {/* X axis layout */}
      <Typography variant="subtitle1">X Axis</Typography>
      <TextField
        label="X Axis Title"
        variant="filled"
        value={layout.xaxis?.title?.text || ""}
        onChange={(e) =>
          handleAxisChange("xaxis", "title", { text: e.target.value })
        }
        fullWidth
      />
      {/* Font Size */}
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
      {/* Standoff - distance of title from axis */}
      <TextField
        label="X Axis Title Standoff (distance from axis)"
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
      {/* Rotation Tick */}
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

      {/* Y axis layout */}
      <Typography variant="subtitle1">Y Axis</Typography>
      {/* Text */}
      <TextField
        label="Y Axis Title"
        variant="filled"
        value={layout.yaxis?.title?.text || ""}
        onChange={(e) =>
          handleAxisChange("yaxis", "title", { text: e.target.value })
        }
        fullWidth
      />
      {/* Font Size */}
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
      {/* Standoff - distance of title from axis */}
      <TextField
        label="Y Axis Title Standoff (distance from axis)"
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
      {/* Rotation Tick */}
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
        label="Font"
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

      <Divider sx={{ my: 2, borderColor: "#444" }} />

      <Stack direction="row" spacing={2} justifyContent="flex-end">
        <Button variant="outlined" onClick={handleCancel} disabled={!modified}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSave}
          disabled={!modified}
        >
          Save
        </Button>
      </Stack>
    </Box>
  );
}
