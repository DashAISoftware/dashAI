import React from "react";
import PropTypes from "prop-types";
import { Box, Checkbox, Chip, ListItemText, MenuItem } from "@mui/material";
import { useTranslation } from "react-i18next";
import FormInputWrapper from "./FormInputWrapper";
import { Input } from "./InputStyles";

function MultiSelectInput({
  name,
  value,
  label,
  onChange,
  error,
  description,
  options,
  optionNames,
}) {
  const { i18n } = useTranslation();
  const lang = i18n.language?.split("-")[0] || "en";

  const resolveName = (entry) => {
    if (typeof entry === "string") return entry;
    if (entry && typeof entry === "object")
      return entry[lang] || entry.en || "";
    return String(entry ?? "");
  };

  const handleChange = (event) => {
    const newValue = event.target.value;
    onChange(typeof newValue === "string" ? newValue.split(",") : newValue);
  };

  const getDisplayName = (option) => {
    if (!optionNames) return option;
    const idx = options.indexOf(option);
    return idx >= 0 && idx < optionNames.length
      ? resolveName(optionNames[idx])
      : option;
  };

  return (
    <FormInputWrapper name={name} description={description}>
      <Input
        select
        name={name}
        label={label}
        value={value || []}
        onChange={handleChange}
        error={error !== undefined}
        helperText={error || " "}
        margin="dense"
        SelectProps={{
          multiple: true,
          renderValue: (selected) => (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {selected.map((val) => (
                <Chip key={val} label={getDisplayName(val)} size="small" />
              ))}
            </Box>
          ),
        }}
      >
        {options.map((option, index) => (
          <MenuItem key={option} value={option}>
            <Checkbox checked={(value || []).indexOf(option) > -1} />
            <ListItemText
              primary={optionNames ? resolveName(optionNames[index]) : option}
            />
          </MenuItem>
        ))}
      </Input>
    </FormInputWrapper>
  );
}

MultiSelectInput.propTypes = {
  name: PropTypes.string.isRequired,
  value: PropTypes.arrayOf(PropTypes.string),
  label: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  description: PropTypes.string.isRequired,
  error: PropTypes.string,
  options: PropTypes.arrayOf(PropTypes.string).isRequired,
  optionNames: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
  ),
};

MultiSelectInput.defaultProps = {
  value: [],
  error: undefined,
  optionNames: undefined,
};

export default MultiSelectInput;
