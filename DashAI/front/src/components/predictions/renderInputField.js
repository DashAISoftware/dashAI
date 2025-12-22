import React from "react";
import { TextField, Select, MenuItem, FormControl } from "@mui/material";

export const renderInputField = (
  handleChange,
  rowIndex,
  col,
  typeInfo,
  value,
  placeholder,
) => {
  const { dtype, type, categories } = typeInfo || {};
  const effectiveType = type || dtype || "string";

  if (effectiveType === "Categorical" && categories && categories.length > 0) {
    return (
      <FormControl fullWidth size="small">
        <Select
          value={value || ""}
          onChange={(e) => handleChange(rowIndex, col, e.target.value)}
          displayEmpty
          sx={{
            color: "white",
            ".MuiOutlinedInput-notchedOutline": { borderColor: "#555" },
            "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "#888" },
            ".MuiSvgIcon-root": { color: "white" },
          }}
        >
          <MenuItem value="" disabled>
            Select a category
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
          input: { color: "white" },
          "& .MuiOutlinedInput-root": {
            "& fieldset": { borderColor: "#555" },
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
          input: { color: "white" },
          "& .MuiOutlinedInput-root": {
            "& fieldset": { borderColor: "#555" },
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
        style={{ color: "white" }}
      />
    );
  }

  return (
    <TextField
      size="small"
      value={value}
      placeholder={placeholder}
      onChange={(e) => handleChange(rowIndex, col, e.target.value)}
      sx={{
        input: { color: "white" },
        "& .MuiOutlinedInput-root": {
          "& fieldset": { borderColor: "#555" },
          "&:hover fieldset": { borderColor: "#888" },
        },
      }}
    />
  );
};
