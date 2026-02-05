import React from "react";
import { TextField, Select, MenuItem, FormControl } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

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
  const theme = useTheme();
  const { t } = useTranslation(["prediction"]);

  if (effectiveType === "Categorical" && categories && categories.length > 0) {
    return (
      <FormControl fullWidth size="small">
        <Select
          value={value || ""}
          onChange={(e) => handleChange(rowIndex, col, e.target.value)}
          displayEmpty
          sx={{
            color: theme.palette.text.primary,
            ".MuiOutlinedInput-notchedOutline": {
              borderColor: theme.palette.divider,
            },
            "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "#888" },
            ".MuiSvgIcon-root": { color: theme.palette.text.primary },
          }}
        >
          <MenuItem value="" disabled>
            {t("prediction:label.selectCategory")}
          </MenuItem>
          {categories.map((cat, idx) => (
            <MenuItem key={idx} value={cat}>
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
        sx={{
          input: { color: theme.palette.text.primary },
          "& .MuiOutlinedInput-root": {
            "& fieldset": { borderColor: theme.palette.divider },
            "&:hover fieldset": { borderColor: "#888" },
          },
        }}
      />
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
        sx={{
          input: { color: theme.palette.text.primary },
          "& .MuiOutlinedInput-root": {
            "& fieldset": { borderColor: theme.palette.divider },
            "&:hover fieldset": { borderColor: "#888" },
          },
        }}
      />
    );
  }

  if (effectiveType === "Image" || dtype === "image") {
    return (
      <input
        type="file"
        accept="image/*"
        onChange={(e) => handleChange(rowIndex, col, e.target.files?.[0])}
        style={{ color: theme.palette.text.primary }}
      />
    );
  }

  return (
    <TextField1
      size="small"
      value={value}
      placeholder={placeholder}
      onChange={(e) => handleChange(rowIndex, col, e.target.value)}
      sx={{
        input: { color: theme.palette.text.primary },
        "& .MuiOutlinedInput-root": {
          "& fieldset": { borderColor: theme.palette.divider },
          "&:hover fieldset": { borderColor: "#888" },
        },
      }}
    />
  );
}

export default InputField;
