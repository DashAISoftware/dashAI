import {
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  OutlinedInput,
  Button,
} from "@mui/material";

import { useTranslation } from "react-i18next";

const MULTILINE_FIELD_KEYS = ["system_prompt"];

export default function AgentConfigField({
  fieldKey,
  fieldSchema,
  value,
  onChange,
}) {
  const { t, i18n } = useTranslation(["agent"]);
  const type = fieldSchema.type;
  const label = fieldSchema.title || fieldKey;
  const description = fieldSchema.description || "";

  if (type === "string" && Array.isArray(fieldSchema.enum)) {
    return (
      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
        <InputLabel>{label}</InputLabel>
        <Select
          value={value ?? ""}
          label={label}
          onChange={(event) => onChange(fieldKey, event.target.value)}
        >
          {fieldSchema.enum.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </Select>
        {description && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
            {description}
          </Typography>
        )}
      </FormControl>
    );
  }

  if (type === "array" && Array.isArray(fieldSchema.items?.enum)) {
    const options = fieldSchema.items.enum;
    const selectedValues = Array.isArray(value) ? value : [];
    const allSelected =
      options.length > 0 && selectedValues.length === options.length;
    const labels = fieldSchema.optionLabels || [];
    const currentLanguage = i18n.language?.split("-")[0] || "en"; // normaliza "es-CL" -> "es"

    const getLabel = (option) => {
      const index = options.indexOf(option);
      const labelEntry = labels[index];

      if (!labelEntry || typeof labelEntry !== "object") {
        return option;
      }

      return labelEntry[currentLanguage] || labelEntry.en || option;
    };

    return (
      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
        <InputLabel>{label}</InputLabel>
        <Select
          multiple
          value={selectedValues}
          input={<OutlinedInput label={label} />}
          onChange={(event) => {
            const nextValue = event.target.value;
            onChange(
              fieldKey,
              typeof nextValue === "string" ? nextValue.split(",") : nextValue,
            );
          }}
          renderValue={(selected) =>
            selected.map((option) => getLabel(option)).join(", ")
          }
        >
          {options.map((option) => (
            <MenuItem key={option} value={option}>
              <Checkbox checked={selectedValues.indexOf(option) > -1} />
              <ListItemText primary={getLabel(option)} />
            </MenuItem>
          ))}
        </Select>

        <Button
          variant="text"
          size="small"
          sx={{ alignSelf: "flex-start", mt: 0.5, mb: 0.5, px: 0 }}
          onClick={() => onChange(fieldKey, allSelected ? [] : [...options])}
        >
          {allSelected
            ? t("agent:button.deselectAll")
            : t("agent:button.selectAll")}
        </Button>

        {description && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
            {description}
          </Typography>
        )}
      </FormControl>
    );
  }

  if (type === "boolean") {
    return (
      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
        <InputLabel>{label}</InputLabel>
        <Select
          value={value === true ? "true" : value === false ? "false" : ""}
          label={label}
          onChange={(event) =>
            onChange(fieldKey, event.target.value === "true")
          }
        >
          <MenuItem value="true">True</MenuItem>
          <MenuItem value="false">False</MenuItem>
        </Select>
        {description && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
            {description}
          </Typography>
        )}
      </FormControl>
    );
  }

  const isNumericField = type === "integer" || type === "number";
  const isMultilineField =
    type === "string" && MULTILINE_FIELD_KEYS.includes(fieldKey);

  return (
    <TextField
      fullWidth
      size="small"
      label={label}
      type={isNumericField ? "number" : "text"}
      value={value ?? ""}
      onChange={(event) => {
        const nextValue = event.target.value;
        if (!isNumericField) {
          onChange(fieldKey, nextValue);
          return;
        }

        if (nextValue === "") {
          onChange(fieldKey, "");
          return;
        }

        const parsedValue =
          type === "integer" ? parseInt(nextValue, 10) : parseFloat(nextValue);
        onChange(fieldKey, Number.isNaN(parsedValue) ? "" : parsedValue);
      }}
      multiline={isMultilineField}
      minRows={isMultilineField ? 4 : undefined}
      sx={{ mb: 2 }}
      helperText={description}
    />
  );
}
