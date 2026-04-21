import React from "react";
import {
  TextField,
  Select,
  MenuItem,
  FormControl,
  Box,
  Button,
} from "@mui/material";
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

  const commonStyles = {
    "& .MuiOutlinedInput-root": {
      fontSize: "0.875rem",
      backgroundColor: theme.palette.background.paper,
      "& fieldset": {
        borderColor: theme.palette.divider,
        borderWidth: "1px",
      },
      "&:hover fieldset": {
        borderColor: theme.palette.primary.main,
      },
      "&.Mui-focused fieldset": {
        borderColor: theme.palette.primary.main,
        borderWidth: "2px",
      },
    },
    "& .MuiInputBase-input": {
      padding: "6px 10px",
      color: theme.palette.text.primary,
    },
  };

  if (effectiveType === "Categorical" && categories && categories.length > 0) {
    return (
      <FormControl fullWidth size="small">
        <Select
          value={value || ""}
          onChange={(e) => handleChange(rowIndex, col, e.target.value)}
          displayEmpty
          sx={{
            fontSize: "0.875rem",
            backgroundColor: theme.palette.background.paper,
            "& .MuiOutlinedInput-notchedOutline": {
              borderColor: theme.palette.divider,
              borderWidth: "1px",
            },
            "&:hover .MuiOutlinedInput-notchedOutline": {
              borderColor: theme.palette.primary.main,
            },
            "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
              borderColor: theme.palette.primary.main,
              borderWidth: "2px",
            },
            "& .MuiSelect-select": {
              padding: "6px 10px",
              color: theme.palette.text.primary,
            },
            "& .MuiSvgIcon-root": {
              color: theme.palette.text.secondary,
            },
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
        fullWidth
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
        sx={commonStyles}
      />
    );
  }

  if (effectiveType === "Image" || dtype === "image") {
    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
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
        fullWidth
        size="small"
        value={value}
        placeholder={placeholder}
        onChange={(e) => handleChange(rowIndex, col, e.target.value)}
        sx={commonStyles}
      />
    );
  }

  return (
    <TextField
      fullWidth
      size="small"
      value={value}
      placeholder={placeholder}
      onChange={(e) => handleChange(rowIndex, col, e.target.value)}
      sx={commonStyles}
    />
  );
}

export default InputField;
