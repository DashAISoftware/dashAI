import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import FormInputWrapper from "./FormInputWrapper";
import {
  FormControl,
  FormControlLabel,
  Switch,
  FormHelperText,
} from "@mui/material";
import InputWithDebounce from "../../shared/InputWithDebounce";

/**
 * This component renders an HPO form field for "number" parameters.
 * It merges the real user data (props.value) with placeholder defaults,
 * ensuring that next time we open the dialog, we see updated data rather than the old placeholder.
 */
function OptimizeNumberInput({
  name,
  label,
  value,
  onChange,
  description,
  error,
  placeholder,
}) {
  // 1) Merge existing user data with defaults from placeholder (if user data is missing)
  //    e.g. if 'value.optimize' is undefined, fallback to placeholder.optimize or false
  const mergedOptimize = value.optimize ?? placeholder.optimize ?? false;
  const mergedLower = value.lower_bound ?? placeholder.lower_bound ?? "";
  const mergedUpper = value.upper_bound ?? placeholder.upper_bound ?? "";
  const mergedFixed = value.fixed_value ?? placeholder.fixed_value ?? "";

  // 2) Keep local state for the switch, so toggling is immediate in the UI
  const [switchState, setSwitchState] = useState(mergedOptimize);

  // If the parent changes value.optimize from outside, sync local switch state:
  useEffect(() => {
    setSwitchState(mergedOptimize);
  }, [mergedOptimize]);

  // 3) Handlers to reflect user input back into the parent form data
  const handleSwitchChange = () => {
    const toggled = !switchState;
    setSwitchState(toggled);
    // Spread the entire "value" and override 'optimize'
    onChange({ ...value, optimize: toggled });
  };

  const handleChangeLower = (inputValue) => {
    const parsed = inputValue === "" ? null : parseFloat(inputValue);
    onChange({ ...value, lower_bound: parsed });
  };

  const handleChangeUpper = (inputValue) => {
    const parsed = inputValue === "" ? null : parseFloat(inputValue);
    onChange({ ...value, upper_bound: parsed });
  };

  const handleChangeFixed = (inputValue) => {
    const parsed = inputValue === "" ? null : parseFloat(inputValue);
    onChange({ ...value, fixed_value: parsed });
  };

  // 4) If 'optimize' is recognized in placeholder, we show the switch & bound inputs
  const canOptimize = placeholder.optimize !== undefined;

  return (
    <FormInputWrapper name={name} description={description}>
      {/* If we can optimize, show the switch control */}
      {canOptimize && (
        <FormControl error={Boolean(error)}>
          <FormControlLabel
            label={`Optimize hyperparameter "${name}"`}
            control={
              <Switch
                name={name}
                checked={switchState}
                onChange={handleSwitchChange}
              />
            }
          />
          <FormHelperText>{error || " "}</FormHelperText>
        </FormControl>
      )}

      {canOptimize && switchState ? (
        // If user toggled "optimize", show lower/upper bound
        <>
          <InputWithDebounce
            variant="outlined"
            label="enter a value for the lower bound of search space"
            name={`${name}-lower`}
            value={mergedLower}
            onChange={handleChangeLower}
            error={Boolean(error)}
            helperText={error || " "}
            type="number"
            margin="dense"
          />
          <InputWithDebounce
            variant="outlined"
            label="enter a value for the upper bound of search space"
            name={`${name}-upper`}
            value={mergedUpper}
            onChange={handleChangeUpper}
            error={Boolean(error)}
            helperText={error || " "}
            type="number"
            margin="dense"
          />
        </>
      ) : (
        // If "optimize" is off (or we can't optimize), show a single "fixed_value"
        <InputWithDebounce
          variant="outlined"
          label="enter a value"
          name={`${name}-fixed`}
          value={mergedFixed}
          onChange={handleChangeFixed}
          error={Boolean(error)}
          helperText={error || " "}
          type="number"
          margin="dense"
        />
      )}
    </FormInputWrapper>
  );
}

OptimizeNumberInput.propTypes = {
  name: PropTypes.string,
  label: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  value: PropTypes.shape({
    optimize: PropTypes.bool,
    fixed_value: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.oneOf([null]),
    ]),
    lower_bound: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.oneOf([null]),
    ]),
    upper_bound: PropTypes.oneOfType([
      PropTypes.number,
      PropTypes.oneOf([null]),
    ]),
  }),
  onChange: PropTypes.func.isRequired,
  placeholder: PropTypes.shape({
    // The original defaults
    optimize: PropTypes.bool,
    fixed_value: PropTypes.number,
    lower_bound: PropTypes.number,
    upper_bound: PropTypes.number,
  }),
  error: PropTypes.string,
};

OptimizeNumberInput.defaultProps = {
  value: {},
  placeholder: {},
  error: undefined,
};

export default OptimizeNumberInput;
