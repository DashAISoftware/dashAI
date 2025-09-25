import React, { useState, useCallback, useEffect } from "react";
import PropTypes from "prop-types";
import { TextField } from "@mui/material";

function PredictionNameInput({
  defaultPredictionName,
  onValidChange,
  onNameChange,
}) {
  const [predictName, setPredictName] = useState("");
  const [predictNameError, setPredictNameError] = useState(false);
  const [hasUserTouchedName, setHasUserTouchedName] = useState(false);

  const isValidPredictName = (name) => {
    return name.length >= 4 && /^[a-zA-Z0-9_-]+$/.test(name);
  };

  const validate = useCallback(
    (name) => {
      const trimmedName = name.trim();
      let isValid = false;
      let hasError = false;

      if (trimmedName === "") {
        if (hasUserTouchedName) {
          isValid = false;
          hasError = false;
        } else {
          isValid = isValidPredictName(defaultPredictionName || "");
          hasError = false;
        }
      } else {
        isValid = isValidPredictName(trimmedName);
        hasError = !isValid;
      }

      setPredictNameError(hasError);
      onValidChange(isValid);
      return isValid;
    },
    [defaultPredictionName, hasUserTouchedName, onValidChange],
  );

  const handleChange = (event) => {
    const value = event.target.value;
    setHasUserTouchedName(true);
    setPredictName(value);
    onNameChange(value);
    validate(value);
  };

  // initialize default value if given
  useEffect(() => {
    if (defaultPredictionName && !predictName.trim() && !hasUserTouchedName) {
      setPredictName(defaultPredictionName);
      onNameChange(defaultPredictionName);
      validate(defaultPredictionName);
    }
  }, [
    defaultPredictionName,
    predictName,
    hasUserTouchedName,
    onNameChange,
    validate,
  ]);

  return (
    <TextField
      id="predict-name-input"
      label="Prediction name"
      value={predictName}
      fullWidth
      onChange={handleChange}
      autoComplete="off"
      sx={{ mb: 4 }}
      error={!!((predictName === "" && hasUserTouchedName) || predictNameError)}
      helperText={
        predictName === "" && hasUserTouchedName
          ? "Name is required"
          : predictNameError
          ? "The prediction name must have at least 4 alphanumeric characters."
          : ""
      }
      InputLabelProps={{ shrink: true }}
    />
  );
}

PredictionNameInput.propTypes = {
  defaultPredictionName: PropTypes.string,
  onValidChange: PropTypes.func.isRequired, // (boolean) => void
  onNameChange: PropTypes.func.isRequired, // (string) => void
};

export default PredictionNameInput;
