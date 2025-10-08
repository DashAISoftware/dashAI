import React from "react";
import { TextField, Typography } from "@mui/material";

export const renderInputField = (
  handleChange,
  rowIndex,
  col,
  typeInfo,
  value,
  placeholder,
) => {
  const { dtype, type } = typeInfo || {};
  const effectiveType = dtype || type || "string";

  switch (effectiveType.toLowerCase()) {
    case "float":
    case "float64":
    case "float32":
    case "number":
      return (
        <TextField
          size="small"
          type="number"
          value={value}
          placeholder={placeholder}
          onChange={(e) =>
            handleChange(
              rowIndex,
              col,
              e.target.value === "" ? "" : parseFloat(e.target.value),
            )
          }
          sx={{
            input: { color: "white" },
            "& .MuiOutlinedInput-root": {
              "& fieldset": { borderColor: "#555" },
              "&:hover fieldset": { borderColor: "#888" },
            },
          }}
        />
      );

    case "int":
    case "int32":
    case "int64":
      return (
        <TextField
          size="small"
          type="number"
          value={value}
          placeholder={placeholder}
          onChange={(e) =>
            handleChange(
              rowIndex,
              col,
              e.target.value === "" ? "" : parseInt(e.target.value),
            )
          }
          sx={{
            input: { color: "white" },
            "& .MuiOutlinedInput-root": {
              "& fieldset": { borderColor: "#555" },
              "&:hover fieldset": { borderColor: "#888" },
            },
          }}
        />
      );

    case "sequence":
      return (
        <TextField
          size="small"
          value={Array.isArray(value) ? value.join(",") : value}
          placeholder={
            Array.isArray(placeholder) ? placeholder.join(",") : placeholder
          }
          onChange={(e) =>
            handleChange(
              rowIndex,
              col,
              e.target.value
                .split(",")
                .map((x) => x.trim())
                .filter(Boolean),
            )
          }
          sx={{
            input: { color: "white" },
            "& .MuiOutlinedInput-root": {
              "& fieldset": { borderColor: "#555" },
              "&:hover fieldset": { borderColor: "#888" },
            },
          }}
        />
      );

    case "image":
      return (
        <input
          type="file"
          accept="image/*"
          onChange={(e) => handleChange(rowIndex, col, e.target.files?.[0])}
          style={{ color: "white" }}
        />
      );

    case "string":
    default:
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
};
