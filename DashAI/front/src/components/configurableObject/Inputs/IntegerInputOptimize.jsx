import React from "react";
import PropTypes from "prop-types";
import FormInputWrapper from "./FormInputWrapper";
import {
  FormControl,
  FormControlLabel,
  Switch,
  FormHelperText,
} from "@mui/material";
import InputWithDebounce from "../../shared/InputWithDebounce";
import { useTranslation } from "react-i18next";

/**
 * This component renders an HPO form field for "integer" parameters.
 * It merges the real user data (props.value) with placeholder defaults,
 * ensuring that next time we open the dialog, we see updated data rather than the old placeholder.
 */
function OptimizeIntegerInput({
  name,
  label,
  value,
  onChange,
  description,
  error,
  placeholder,
}) {
  const { t } = useTranslation("configurableObject");

  // 0) Split errors into fixed_value vs upper/lower bound for display
  const errors = error
    ? value?.optimize
      ? typeof error === "string"
        ? error
        : (error["upper_bound"] || "") + (error["lower_bound"] || "")
      : error["fixed_value"]
    : null;

  const fixedError = error && !value?.optimize ? error["fixed_value"] : null;
  const upperError =
    error && value?.optimize
      ? typeof error === "string"
        ? error
        : error["upper_bound"] || null
      : null;

  const lowerError =
    error && value?.optimize
      ? typeof error === "string"
        ? error
        : error["lower_bound"] || null
      : null;

  // 1) Merge existing user data with defaults from placeholder (if user data is missing)
  const mergedOptimize = value?.optimize ?? placeholder?.optimize ?? false;
  const mergedLower = value?.lower_bound ?? placeholder?.lower_bound ?? null;
  const mergedUpper = value?.upper_bound ?? placeholder?.upper_bound ?? null;
  const mergedFixed = value?.fixed_value ?? placeholder?.fixed_value ?? null;

  // 2) Handlers to reflect user input back into the parent form data
  const handleSwitchChange = () => {
    const toggled = !mergedOptimize;

    // If switching modes and there was an error, use placeholder values
    const shouldUseePlaceholder = error !== undefined;

    onChange({
      fixed_value: shouldUseePlaceholder
        ? (placeholder?.fixed_value ?? null)
        : mergedFixed,
      lower_bound: shouldUseePlaceholder
        ? (placeholder?.lower_bound ?? null)
        : mergedLower,
      upper_bound: shouldUseePlaceholder
        ? (placeholder?.upper_bound ?? null)
        : mergedUpper,
      optimize: toggled,
    });
  };

  const handleChangeLower = (inputValue) => {
    const parsed = inputValue === "" ? null : parseInt(inputValue, 10);
    onChange({
      ...value,
      lower_bound: isNaN(parsed) ? null : parsed,
    });
  };

  const handleChangeUpper = (inputValue) => {
    const parsed = inputValue === "" ? null : parseInt(inputValue, 10);
    onChange({
      ...value,
      upper_bound: isNaN(parsed) ? null : parsed,
    });
  };

  const handleChangeFixed = (inputValue) => {
    const parsed = inputValue === "" ? null : parseInt(inputValue, 10);
    onChange({
      ...value,
      fixed_value: isNaN(parsed) ? null : parsed,
    });
  };

  // 4) If 'optimize' is recognized in placeholder, we show the switch & bound inputs
  const canOptimize = placeholder?.optimize !== undefined;

  return (
    <FormInputWrapper name={name} description={description}>
      {/* If we can optimize, show the switch control */}
      {canOptimize && (
        <FormControl error={errors !== null}>
          <FormControlLabel
            label={t("optimize", { name: label || name })}
            control={
              <Switch
                name={name}
                checked={mergedOptimize}
                onChange={handleSwitchChange}
              />
            }
          />
        </FormControl>
      )}
      {canOptimize && mergedOptimize ? (
        // If user toggled "optimize", show lower/upper bound
        <>
          <InputWithDebounce
            variant="outlined"
            label={t("lowerBound")}
            name={`${name}-lower`}
            value={mergedLower !== null ? mergedLower : ""}
            onChange={handleChangeLower}
            error={lowerError !== null}
            helperText={lowerError || " "}
            type="number"
            margin="dense"
            inputProps={{ step: 1 }}
          />
          <InputWithDebounce
            variant="outlined"
            label={t("upperBound")}
            name={`${name}-upper`}
            value={mergedUpper !== null ? mergedUpper : ""}
            onChange={handleChangeUpper}
            error={upperError !== null}
            helperText={upperError || " "}
            type="number"
            margin="dense"
            inputProps={{ step: 1 }}
          />
        </>
      ) : (
        // If "optimize" is off (or we can't optimize), show a single "fixed_value"
        <InputWithDebounce
          variant="outlined"
          label={label || t("enterValue")}
          name={`${name}-fixed`}
          value={mergedFixed !== null ? mergedFixed : ""}
          onChange={handleChangeFixed}
          error={fixedError !== null}
          helperText={fixedError || " "}
          type="number"
          margin="dense"
          inputProps={{ step: 1 }}
        />
      )}
    </FormInputWrapper>
  );
}

OptimizeIntegerInput.propTypes = {
  name: PropTypes.string.isRequired,
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
  label: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  description: PropTypes.string,
  error: PropTypes.string,
  placeholder: PropTypes.shape({
    optimize: PropTypes.bool,
    fixed_value: PropTypes.number,
    lower_bound: PropTypes.number,
    upper_bound: PropTypes.number,
  }),
};

OptimizeIntegerInput.defaultProps = {
  value: {},
  placeholder: {},
  error: undefined,
  description: "",
};

export default OptimizeIntegerInput;
