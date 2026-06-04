import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import FormInputWrapper from "./FormInputWrapper";
import {
  FormControl,
  FormControlLabel,
  Switch,
  Box,
  Typography,
} from "@mui/material";
import InputWithDebounce from "../../shared/InputWithDebounce";
import { useTranslation } from "react-i18next";

/**
 * Renders an HPO form field for "number" parameters.
 *
 * When `externalSwitchState` is provided the optimize toggle is controlled by the
 * parent (e.g. FormSchemaFieldWithOptimizers renders it in the card header) and the
 * internal switch UI is hidden.
 */
function OptimizeNumberInput({
  name,
  label,
  value = {},
  onChange,
  description = "",
  error = undefined,
  placeholder = {},
  externalSwitchState,
}) {
  const { t } = useTranslation("configurableObject");

  const mergedOptimize = value?.optimize ?? placeholder?.optimize ?? false;
  const mergedLower = value?.lower_bound ?? placeholder?.lower_bound ?? null;
  const mergedUpper = value?.upper_bound ?? placeholder?.upper_bound ?? null;
  const mergedFixed = value?.fixed_value ?? placeholder?.fixed_value ?? null;

  const [internalSwitchState, setInternalSwitchState] =
    useState(mergedOptimize);

  const isExternallyControlled = externalSwitchState !== undefined;
  const switchState = isExternallyControlled
    ? externalSwitchState
    : internalSwitchState;

  useEffect(() => {
    if (!isExternallyControlled) {
      setInternalSwitchState(mergedOptimize);
    }
  }, [mergedOptimize, isExternallyControlled]);

  const fixedError = error && !switchState ? error["fixed_value"] : null;
  const upperError =
    error && switchState
      ? typeof error === "string"
        ? error
        : error["upper_bound"] || null
      : null;
  const lowerError =
    error && switchState
      ? typeof error === "string"
        ? error
        : error["lower_bound"] || null
      : null;

  const handleSwitchChange = () => {
    if (isExternallyControlled) return;
    const toggled = !internalSwitchState;
    setInternalSwitchState(toggled);
    const shouldUsePlaceholder = error !== undefined;
    onChange({
      fixed_value: shouldUsePlaceholder
        ? (placeholder?.fixed_value ?? null)
        : mergedFixed,
      lower_bound: shouldUsePlaceholder
        ? (placeholder?.lower_bound ?? null)
        : mergedLower,
      upper_bound: shouldUsePlaceholder
        ? (placeholder?.upper_bound ?? null)
        : mergedUpper,
      optimize: toggled,
    });
  };

  const handleChangeLower = (inputValue) => {
    const parsed = inputValue === "" ? null : parseFloat(inputValue);
    onChange({ ...value, lower_bound: isNaN(parsed) ? null : parsed });
  };

  const handleChangeUpper = (inputValue) => {
    const parsed = inputValue === "" ? null : parseFloat(inputValue);
    onChange({ ...value, upper_bound: isNaN(parsed) ? null : parsed });
  };

  const handleChangeFixed = (inputValue) => {
    const parsed = inputValue === "" ? null : parseFloat(inputValue);
    onChange({ ...value, fixed_value: isNaN(parsed) ? null : parsed });
  };

  const canOptimize = placeholder?.optimize !== undefined;

  return (
    <FormInputWrapper name={name} description={description}>
      {canOptimize && !isExternallyControlled && (
        <FormControl>
          <FormControlLabel
            label={t("optimize", { name: label || name })}
            control={
              <Switch
                name={name}
                checked={switchState}
                onChange={handleSwitchChange}
              />
            }
          />
        </FormControl>
      )}
      {canOptimize && switchState ? (
        <Box display="flex" gap={4}>
          <Box flex={1}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mb: 1, display: "block" }}
            >
              {t("lowerBound")}
            </Typography>
            <InputWithDebounce
              variant="outlined"
              size="small"
              name={`${name}-lower`}
              value={mergedLower !== null ? mergedLower : ""}
              onChange={handleChangeLower}
              error={lowerError !== null}
              helperText={lowerError}
              type="number"
              sx={{ width: "100%" }}
            />
          </Box>
          <Box flex={1}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mb: 1, display: "block" }}
            >
              {t("upperBound")}
            </Typography>
            <InputWithDebounce
              variant="outlined"
              size="small"
              name={`${name}-upper`}
              value={mergedUpper !== null ? mergedUpper : ""}
              onChange={handleChangeUpper}
              error={upperError !== null}
              helperText={upperError}
              type="number"
              sx={{ width: "100%" }}
            />
          </Box>
        </Box>
      ) : (
        <InputWithDebounce
          variant="outlined"
          size="small"
          label={label || t("enterValue")}
          name={`${name}-fixed`}
          value={mergedFixed !== null ? mergedFixed : ""}
          onChange={handleChangeFixed}
          error={fixedError !== null}
          helperText={fixedError}
          type="number"
        />
      )}
    </FormInputWrapper>
  );
}

OptimizeNumberInput.propTypes = {
  name: PropTypes.string,
  label: PropTypes.string,
  description: PropTypes.string,
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
    optimize: PropTypes.bool,
    fixed_value: PropTypes.number,
    lower_bound: PropTypes.number,
    upper_bound: PropTypes.number,
  }),
  error: PropTypes.string,
  externalSwitchState: PropTypes.bool,
};

export default OptimizeNumberInput;
