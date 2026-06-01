import React from "react";
import {
  TextField,
  Select,
  MenuItem,
  FormControl,
  Box,
  Button,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import {
  MIN_INPUT_WIDTH,
  CHAR_WIDTH_PX,
  INPUT_PADDING_PX,
} from "./inputFieldConstants";

function computeWidth(val, placeholder) {
  const len = Math.max(
    String(val ?? "").length,
    String(placeholder ?? "").length,
  );
  return Math.max(MIN_INPUT_WIDTH, len * CHAR_WIDTH_PX + INPUT_PADDING_PX);
}

function InputField({
  handleChange,
  rowIndex,
  col,
  typeInfo,
  value,
  placeholder,
}) {
  const { dtype, type, categories } = typeInfo || {};
  const effectiveType = type || dtype || "string";
  const { t } = useTranslation(["prediction"]);

  // commonStyles is static — no useTheme needed. Emotion resolves theme
  // tokens at style-injection time, so `theme.palette.*` inside `sx` is
  // fine as a CSS variable reference without calling useTheme here.
  const commonStyles = {
    "& .MuiOutlinedInput-root": {
      fontSize: "0.875rem",
      "& fieldset": { borderWidth: "1px" },
      "&.Mui-focused fieldset": { borderWidth: "2px" },
    },
    "& .MuiInputBase-input": { padding: "6px 10px" },
  };

  if (effectiveType === "Categorical" && categories && categories.length > 0) {
    return (
      <FormControl size="small" sx={{ minWidth: MIN_INPUT_WIDTH }}>
        <Select
          value={value || ""}
          onChange={(e) => handleChange(rowIndex, col, e.target.value)}
          displayEmpty
          sx={{
            fontSize: "0.875rem",
            "& .MuiOutlinedInput-notchedOutline": { borderWidth: "1px" },
            "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
              borderWidth: "2px",
            },
            "& .MuiSelect-select": { padding: "6px 10px" },
          }}
        >
          <MenuItem value="" disabled sx={{ fontSize: "0.875rem" }}>
            {t("prediction:label.selectCategory")}
          </MenuItem>
          {categories.map((cat, idx) => (
            <MenuItem key={idx} value={cat} sx={{ fontSize: "0.875rem" }}>
              {cat}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  }

  if (
    effectiveType === "Float" ||
    effectiveType === "Integer" ||
    dtype?.startsWith("float") ||
    dtype?.startsWith("int")
  ) {
    const isInteger = effectiveType === "Integer" || dtype?.startsWith("int");

    return (
      <TextField
        size="small"
        type="number"
        value={value}
        placeholder={placeholder}
        inputProps={{
          step: isInteger ? 1 : "any",
        }}
        onChange={(e) => {
          const val =
            e.target.value === ""
              ? ""
              : isInteger
                ? parseInt(e.target.value)
                : parseFloat(e.target.value);
          handleChange(rowIndex, col, val);
        }}
        sx={{ width: computeWidth(value, placeholder), ...commonStyles }}
      />
    );
  }

  if (effectiveType === "Image" || dtype === "image") {
    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
        }}
      >
        {value instanceof File && (
          <img
            src={URL.createObjectURL(value)}
            alt="preview"
            style={{
              maxHeight: 40,
              maxWidth: 40,
              objectFit: "contain",
              borderRadius: 4,
            }}
          />
        )}
        <Button
          variant="outlined"
          component="label"
          size="small"
          sx={{ textTransform: "none", fontSize: "0.8rem" }}
        >
          {value instanceof File
            ? t("prediction:label.changeImage")
            : t("prediction:label.uploadImage")}
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleChange(rowIndex, col, file);
            }}
          />
        </Button>
      </Box>
    );
  }

  if (
    effectiveType === "Text" ||
    effectiveType === "string" ||
    dtype === "string"
  ) {
    return (
      <TextField
        size="small"
        value={value}
        placeholder={placeholder}
        onChange={(e) => handleChange(rowIndex, col, e.target.value)}
        sx={{ width: computeWidth(value, placeholder), ...commonStyles }}
      />
    );
  }

  return (
    <TextField
      size="small"
      value={value}
      placeholder={placeholder}
      onChange={(e) => handleChange(rowIndex, col, e.target.value)}
      sx={{ width: computeWidth(value, placeholder), ...commonStyles }}
    />
  );
}

export default React.memo(InputField);
