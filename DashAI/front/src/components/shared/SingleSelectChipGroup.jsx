import { ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import React from "react";
import PropTypes from "prop-types";

/**
 * This component is a single select toggle group — the options are rendered
 * as one connected control (not separate buttons) so it reads as a switch
 * between mutually exclusive choices, e.g. "Int" vs "Null" for a nullable
 * field's type.
 * @param {Array} options - The options to display
 * @param {function} onChange - The function to update the selected option
 * @param {string} selected - The selected option
 */

const SingleSelectChipGroup = ({ options, onChange, selected }) => {
  const theme = useTheme();

  const handleChange = (event, value) => {
    if (value !== null) onChange(value);
  };

  return (
    <ToggleButtonGroup
      value={selected}
      exclusive
      onChange={handleChange}
      size="small"
      aria-label="type selector"
      sx={{ bgcolor: theme.palette.ui.box, borderRadius: 1 }}
    >
      {options.map((option, index) => (
        <ToggleButton
          key={"option-" + option.key + "-" + index}
          value={option.key}
          sx={{
            textTransform: "none",
            px: 3,
            border: "1px solid transparent",
            color: "text.secondary",
            // A soft tint (not a solid fill, which read too much like the
            // app's primary action buttons) marks the active option.
            "&.Mui-selected": {
              bgcolor: "action.selected",
              color: "primary.main",
              fontWeight: 600,
              "&:hover": { bgcolor: "action.selected" },
            },
          }}
        >
          {option.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
};

SingleSelectChipGroup.propTypes = {
  options: PropTypes.array.isRequired,
  onChange: PropTypes.func.isRequired,
  selected: PropTypes.string.isRequired,
};

export default SingleSelectChipGroup;
