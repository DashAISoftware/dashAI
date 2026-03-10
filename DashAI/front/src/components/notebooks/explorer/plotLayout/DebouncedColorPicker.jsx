import React, { useRef, useState, useEffect } from "react";
import { Box, TextField } from "@mui/material";

export default function DebouncedColorPicker({
  label,
  value,
  onChange,
  delay = 300,
}) {
  const [localValue, setLocalValue] = useState(value || "#000000");
  const timeoutRef = useRef(null);

  // Helper to expand 3-digit hex to 6-digit
  const expandHex = (hex) => {
    if (/^#[0-9A-Fa-f]{3}$/.test(hex)) {
      return "#" + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3];
    }
    return hex;
  };

  // Convert RGB to hex for the color input
  const rgbToHex = (rgb) => {
    if (!rgb || !rgb.startsWith("rgb(")) return rgb;

    try {
      const matches = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
      if (!matches) return rgb;

      const r = parseInt(matches[1]);
      const g = parseInt(matches[2]);
      const b = parseInt(matches[3]);

      return (
        "#" +
        r.toString(16).padStart(2, "0") +
        g.toString(16).padStart(2, "0") +
        b.toString(16).padStart(2, "0")
      );
    } catch (error) {
      return rgb;
    }
  };

  // Convert hex to RGB
  const hexToRgb = (hex) => {
    if (!hex || !hex.startsWith("#")) return hex;

    try {
      // Expand shorthand hex
      const fullHex = expandHex(hex);
      if (!/^#[0-9A-Fa-f]{6}$/.test(fullHex)) return hex;

      const r = parseInt(fullHex.slice(1, 3), 16);
      const g = parseInt(fullHex.slice(3, 5), 16);
      const b = parseInt(fullHex.slice(5, 7), 16);

      return `rgb(${r}, ${g}, ${b})`;
    } catch (error) {
      return hex;
    }
  };

  // Determine if value is RGB format
  const isRgbFormat = (color) => {
    return color && color.startsWith("rgb(");
  };

  // Get display value for color input (always hex)
  const getColorInputValue = (color) => {
    if (isRgbFormat(color)) {
      return rgbToHex(color);
    }
    return expandHex(color);
  };

  // Get display value for text input (preserves original format)
  const getTextInputValue = (color) => {
    return color || "#000000";
  };

  useEffect(() => {
    setLocalValue(value || "#000000");
  }, [value]);

  const handleColorChange = (e) => {
    const newHexValue = e.target.value;
    setLocalValue(newHexValue);

    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    timeoutRef.current = setTimeout(() => {
      // If original value was RGB, convert back to RGB
      if (isRgbFormat(value)) {
        onChange(hexToRgb(newHexValue));
      } else {
        onChange(newHexValue);
      }
    }, delay);
  };

  const handleTextChange = (e) => {
    const newValue = e.target.value;
    setLocalValue(newValue);

    // Clear any pending debounced updates
    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    // Validate and call onChange for both hex and RGB formats
    const isValidHex = /^#([0-9A-Fa-f]{3}){1,2}$/.test(newValue);
    const isValidRgb = /^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$/.test(newValue);

    if (isValidHex || isValidRgb) {
      timeoutRef.current = setTimeout(() => {
        onChange(newValue);
      }, delay);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        gap: 2,
        width: "100%",
      }}
    >
      <TextField
        label={label}
        variant="filled"
        type="color"
        value={getColorInputValue(localValue)}
        onChange={handleColorChange}
        sx={{ flex: 1 }}
        InputLabelProps={{ shrink: true }}
      />
      <TextField
        variant="filled"
        value={getTextInputValue(localValue)}
        onChange={handleTextChange}
        placeholder="#000000 or rgb(0,0,0)"
        sx={{ width: "140px" }}
        helperText={isRgbFormat(localValue) ? "RGB" : "HEX"}
      />
    </Box>
  );
}
